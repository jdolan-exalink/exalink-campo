import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
import aiomqtt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.device import Device
from app.models.animal import Animal
from app.models.location import Location
from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus
from app.models.alert_config import AlertConfig
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

logger = logging.getLogger(__name__)

TOPIC_LOCATION = "exalink/+/devices/+/location"
TOPIC_STATUS = "exalink/+/devices/+/status"


async def _load_configs(db: AsyncSession, tenant_id) -> dict[AlertType, AlertConfig]:
    result = await db.execute(
        select(AlertConfig).where(AlertConfig.tenant_id == tenant_id)
    )
    return {cfg.alert_type: cfg for cfg in result.scalars().all()}


async def _maybe_alert(
    db: AsyncSession,
    tenant_id,
    alert_type: AlertType,
    configs: dict[AlertType, AlertConfig],
    *,
    device_id=None,
    animal_id=None,
    title: str,
    message: str,
    fallback_severity: AlertSeverity = AlertSeverity.WARNING,
) -> None:
    """Crea una alerta respetando la configuración (enabled, repeat, browser_notify).

    Deduplica: si existe una alerta OPEN del mismo tipo+device, sólo se vuelve a
    notificar si pasó el repeat_interval_minutes desde last_notified_at.
    """
    cfg = configs.get(alert_type)
    if cfg and not cfg.enabled:
        return

    severity = cfg.severity if cfg else fallback_severity

    # Buscar alerta abierta existente del mismo tipo y dispositivo
    q = select(Alert).where(
        Alert.tenant_id == tenant_id,
        Alert.alert_type == alert_type,
        Alert.status == AlertStatus.OPEN,
    )
    if device_id is not None:
        q = q.where(Alert.device_id == device_id)
    else:
        q = q.where(Alert.title == title)
    result = await db.execute(q)
    existing = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if existing:
        repeat_min = cfg.repeat_interval_minutes if cfg else 0
        if repeat_min <= 0:
            return
        last = existing.last_notified_at or existing.created_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if now - last < timedelta(minutes=repeat_min):
            return
        existing.last_notified_at = now
        existing.notified = True
        return

    alert = Alert(
        tenant_id=tenant_id,
        device_id=device_id,
        animal_id=animal_id,
        alert_type=alert_type,
        severity=severity,
        status=AlertStatus.OPEN,
        title=title,
        message=message,
        notified=True,
        last_notified_at=now,
        created_by=None,
    )
    db.add(alert)


async def process_location(payload: dict, db: AsyncSession) -> None:
    device_uid = payload.get("device_id")
    lat = payload.get("lat")
    lon = payload.get("lon")
    if not device_uid or lat is None or lon is None:
        return

    result = await db.execute(select(Device).where(Device.device_uid == device_uid, Device.is_active == True))
    device = result.scalar_one_or_none()
    if not device:
        logger.warning("Dispositivo desconocido: %s", device_uid)
        return

    ts = payload.get("timestamp")
    timestamp = datetime.fromisoformat(ts) if ts else datetime.now(timezone.utc)
    point = from_shape(Point(lon, lat), srid=4326)

    # Update device state
    device.last_location = point
    device.last_seen = timestamp
    device.is_online = True
    if payload.get("battery") is not None:
        device.battery_pct = int(payload["battery"])
    if payload.get("rssi") is not None:
        device.rssi = int(payload["rssi"])
    if payload.get("temperature") is not None:
        device.temperature = float(payload["temperature"])
    if payload.get("activity_score") is not None:
        device.activity_score = int(payload["activity_score"])

    # Save location record
    loc = Location(
        tenant_id=device.tenant_id,
        device_id=device.id,
        animal_id=device.animal_id,
        timestamp=timestamp,
        point=point,
        battery_pct=payload.get("battery"),
        rssi=payload.get("rssi"),
        temperature=payload.get("temperature"),
        activity_score=payload.get("activity_score"),
        speed_kmh=payload.get("speed"),
        altitude_m=payload.get("altitude"),
    )
    db.add(loc)

    configs = await _load_configs(db, device.tenant_id)

    # Low battery alert (umbral configurable)
    battery = payload.get("battery")
    if battery is not None and device.animal_id is not None:
        bat_cfg = configs.get(AlertType.LOW_BATTERY)
        threshold = bat_cfg.threshold_value if bat_cfg else 15
        if threshold is not None and battery <= threshold:
            await _maybe_alert(
                db, device.tenant_id, AlertType.LOW_BATTERY, configs,
                device_id=device.id,
                animal_id=device.animal_id,
                title=f"Batería baja: {device.device_uid} ({battery}%)",
                message=f"El dispositivo {device.device_uid} tiene {battery}% de batería.",
            )

    # Temperature alerts (umbrales configurables)
    temp = payload.get("temperature")
    if temp is not None and device.animal_id is not None:
        tlow = configs.get(AlertType.TEMPERATURE_LOW)
        thigh = configs.get(AlertType.TEMPERATURE_HIGH)
        if tlow and tlow.threshold_min is not None and temp <= tlow.threshold_min:
            await _maybe_alert(
                db, device.tenant_id, AlertType.TEMPERATURE_LOW, configs,
                device_id=device.id,
                animal_id=device.animal_id,
                title=f"Temperatura baja: {device.device_uid} ({temp}°C)",
                message=f"El dispositivo {device.device_uid} registró {temp}°C.",
                fallback_severity=AlertSeverity.CRITICAL,
            )
        elif thigh and thigh.threshold_max is not None and temp >= thigh.threshold_max:
            await _maybe_alert(
                db, device.tenant_id, AlertType.TEMPERATURE_HIGH, configs,
                device_id=device.id,
                animal_id=device.animal_id,
                title=f"Temperatura alta: {device.device_uid} ({temp}°C)",
                message=f"El dispositivo {device.device_uid} registró {temp}°C.",
                fallback_severity=AlertSeverity.CRITICAL,
            )

    await db.commit()
    logger.debug("Ubicación procesada: %s lat=%s lon=%s", device_uid, lat, lon)


async def process_status(payload: dict, db: AsyncSession) -> None:
    device_uid = payload.get("device_id")
    if not device_uid:
        return
    result = await db.execute(select(Device).where(Device.device_uid == device_uid))
    device = result.scalar_one_or_none()
    if not device:
        return
    device.is_online = payload.get("online", True)
    device.firmware = payload.get("firmware", device.firmware)
    await db.commit()


async def run_mqtt_consumer() -> None:
    logger.info("Iniciando MQTT consumer — broker=%s:%s", settings.MQTT_HOST, settings.MQTT_PORT)
    reconnect_interval = 5
    while True:
        try:
            async with aiomqtt.Client(
                hostname=settings.MQTT_HOST,
                port=settings.MQTT_PORT,
                username=settings.MQTT_USERNAME or None,
                password=settings.MQTT_PASSWORD or None,
            ) as client:
                logger.info("MQTT conectado")
                await client.subscribe(TOPIC_LOCATION)
                await client.subscribe(TOPIC_STATUS)
                async for message in client.messages:
                    topic = str(message.topic)
                    try:
                        payload = json.loads(message.payload.decode())
                    except json.JSONDecodeError:
                        logger.warning("Payload JSON inválido en %s", topic)
                        continue

                    async with AsyncSessionLocal() as db:
                        try:
                            if "/location" in topic:
                                await process_location(payload, db)
                            elif "/status" in topic:
                                await process_status(payload, db)
                        except Exception as e:
                            logger.error("Error procesando mensaje: %s", e)
                            await db.rollback()
        except aiomqtt.MqttError as e:
            logger.warning("MQTT desconectado (%s), reconectando en %ds...", e, reconnect_interval)
            await asyncio.sleep(reconnect_interval)
        except Exception as e:
            logger.error("Error inesperado en MQTT consumer: %s", e)
            await asyncio.sleep(reconnect_interval)
