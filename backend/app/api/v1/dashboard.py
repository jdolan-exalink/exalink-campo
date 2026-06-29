from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.animal import Animal, AnimalStatus
from app.models.device import Device, DeviceType
from app.models.paddock import Paddock
from app.models.alert import Alert, AlertStatus, AlertSeverity, AlertType
from app.models.location import Location
from app.models.establishment import Establishment
from geoalchemy2.shape import to_shape
from datetime import datetime, timezone, timedelta
from app.api.v1.lora import _get_db as _get_lora_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/kpis")
async def get_kpis(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    tid = current_user.tenant_id

    total_animals = await db.scalar(
        select(func.count(Animal.id)).where(Animal.tenant_id == tid, Animal.status == AnimalStatus.ACTIVE)
    )
    monitored = await db.scalar(
        select(func.count(Device.id)).where(
            Device.tenant_id == tid, Device.is_active == True,
            Device.animal_id.isnot(None), Device.device_type.in_(["gps_collar", "gps_tag"])
        )
    )
    paddocks_occupied = await db.scalar(
        select(func.count(Paddock.id)).where(
            Paddock.tenant_id == tid, Paddock.is_active == True, Paddock.current_load > 0
        )
    )
    total_paddocks = await db.scalar(
        select(func.count(Paddock.id)).where(Paddock.tenant_id == tid, Paddock.is_active == True)
    )
    open_alerts = await db.scalar(
        select(func.count(Alert.id)).where(Alert.tenant_id == tid, Alert.status == AlertStatus.OPEN)
    )
    critical_alerts = await db.scalar(
        select(func.count(Alert.id)).where(
            Alert.tenant_id == tid, Alert.status == AlertStatus.OPEN, Alert.severity == AlertSeverity.CRITICAL
        )
    )
    offline_devices = await db.scalar(
        select(func.count(Device.id)).where(Device.tenant_id == tid, Device.is_active == True, Device.is_online == False)
    )
    low_battery = await db.scalar(
        select(func.count(Device.id)).where(
            Device.tenant_id == tid, Device.is_active == True, Device.battery_pct.isnot(None), Device.battery_pct <= 20
        )
    )
    possible_heat = await db.scalar(
        select(func.count(Alert.id)).where(
            Alert.tenant_id == tid, Alert.status == AlertStatus.OPEN, Alert.alert_type == AlertType.POSSIBLE_HEAT
        )
    )
    possible_birth = await db.scalar(
        select(func.count(Alert.id)).where(
            Alert.tenant_id == tid, Alert.status == AlertStatus.OPEN, Alert.alert_type == AlertType.POSSIBLE_BIRTH
        )
    )

    # LoRa device stats
    lora_offline = 0
    lora_low_bat = 0
    try:
        lora_conn = _get_lora_db()
        lora_offline = lora_conn.execute("""
            SELECT COUNT(*) FROM devices d
            WHERE d.last_seen IS NULL
               OR d.last_seen <= datetime('now', 'localtime', '-' || MAX(COALESCE(d.refresh_freq_s, 60), 300) * 3 || ' seconds')
        """).fetchone()[0]
        lora_low_bat = lora_conn.execute("""
            SELECT COUNT(*) FROM devices
            WHERE battery_pct IS NOT NULL AND battery_pct <= 10
        """).fetchone()[0]
        lora_conn.close()
    except Exception:
        pass

    return {
        "total_animals": total_animals or 0,
        "monitored_animals": monitored or 0,
        "total_paddocks": total_paddocks or 0,
        "paddocks_occupied": paddocks_occupied or 0,
        "open_alerts": open_alerts or 0,
        "critical_alerts": critical_alerts or 0,
        "offline_devices": (offline_devices or 0) + lora_offline,
        "low_battery_devices": (low_battery or 0) + lora_low_bat,
        "possible_heat": possible_heat or 0,
        "possible_birth": possible_birth or 0,
    }


@router.get("/map-data")
async def get_map_data(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    tid = current_user.tenant_id

    # Animals with GPS
    devices_result = await db.execute(
        select(Device).where(
            Device.tenant_id == tid,
            Device.is_active == True,
            Device.last_location.isnot(None),
        )
    )
    devices = devices_result.scalars().all()

    animals_on_map = []
    for dev in devices:
        if dev.last_location:
            pt = to_shape(dev.last_location)
            animals_on_map.append({
                "device_id": str(dev.id),
                "device_uid": dev.device_uid,
                "animal_id": str(dev.animal_id) if dev.animal_id else None,
                "lat": pt.y,
                "lon": pt.x,
                "battery_pct": dev.battery_pct,
                "is_online": dev.is_online,
                "last_seen": dev.last_seen.isoformat() if dev.last_seen else None,
                "device_type": dev.device_type.value,
            })

    # Paddocks as GeoJSON
    paddocks_result = await db.execute(
        select(Paddock).where(Paddock.tenant_id == tid, Paddock.is_active == True)
    )
    paddocks = paddocks_result.scalars().all()

    paddock_features = []
    for p in paddocks:
        if p.polygon:
            from shapely.geometry import mapping
            paddock_features.append({
                "type": "Feature",
                "properties": {
                    "id": str(p.id),
                    "name": p.name,
                    "status": p.status.value,
                    "current_load": p.current_load,
                    "max_capacity": p.max_capacity,
                    "color": p.color or "#22c55e",
                },
                "geometry": mapping(to_shape(p.polygon)),
            })

    # Recent alerts (last 20)
    alerts_result = await db.execute(
        select(Alert)
        .where(Alert.tenant_id == tid, Alert.status == AlertStatus.OPEN)
        .order_by(Alert.created_at.desc())
        .limit(20)
    )
    alerts = alerts_result.scalars().all()
    alerts_list = [
        {
            "id": str(a.id),
            "alert_type": a.alert_type.value,
            "severity": a.severity.value,
            "title": a.title,
            "message": a.message,
            "created_at": a.created_at.isoformat(),
            "animal_id": str(a.animal_id) if a.animal_id else None,
        }
        for a in alerts
    ]

    # Gateways from LoRa DB
    gw_list = []
    try:
        lora_conn = _get_lora_db()
        gw_rows = lora_conn.execute("""
            SELECT g.gateway_id, g.name, g.lat, g.lon, g.battery_pct, g.charging,
                   g.temperature, g.humidity, g.last_seen,
                   CASE WHEN g.last_seen IS NOT NULL AND g.last_seen > datetime('now', 'localtime', '-1 hours') THEN 1 ELSE 0 END AS online
            FROM gateways g
            WHERE g.lat IS NOT NULL AND g.lon IS NOT NULL
        """).fetchall()
        for r in gw_rows:
            gw_list.append({
                "gateway_id": r["gateway_id"],
                "name": r["name"],
                "lat": r["lat"],
                "lon": r["lon"],
                "battery_pct": r["battery_pct"],
                "charging": r["charging"],
                "temperature": r["temperature"],
                "humidity": r["humidity"],
                "last_seen": r["last_seen"],
                "online": r["online"],
            })
        lora_conn.close()
    except Exception:
        pass

    return {
        "animals": animals_on_map,
        "gateways": gw_list,
        "paddocks": {"type": "FeatureCollection", "features": paddock_features},
        "alerts": alerts_list,
    }
