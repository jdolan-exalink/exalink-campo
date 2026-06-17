from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.alert import Alert, AlertStatus, AlertSeverity, AlertType
from app.schemas.alert import AlertResponse, AlertCreate
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _serialize(alert: Alert) -> AlertResponse:
    return AlertResponse(
        id=alert.id,
        tenant_id=alert.tenant_id,
        establishment_id=alert.establishment_id,
        animal_id=alert.animal_id,
        device_id=alert.device_id,
        alert_type=alert.alert_type,
        severity=alert.severity,
        status=alert.status,
        title=alert.title,
        message=alert.message,
        created_at=alert.created_at,
        resolved_at=alert.resolved_at,
        animal_ear_tag=alert.animal.ear_tag if alert.animal else None,
        device_uid=alert.device.device_uid if alert.device else None,
    )


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    status: AlertStatus | None = None,
    severity: AlertSeverity | None = None,
    alert_type: AlertType | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(Alert)
        .options(selectinload(Alert.animal), selectinload(Alert.device))
        .where(Alert.tenant_id == current_user.tenant_id)
    )
    if status:
        q = q.where(Alert.status == status)
    if severity:
        q = q.where(Alert.severity == severity)
    if alert_type:
        q = q.where(Alert.alert_type == alert_type)
    q = q.order_by(Alert.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(q)
    return [_serialize(a) for a in result.scalars().all()]


@router.post("", response_model=AlertResponse, status_code=201)
async def create_alert(
    payload: AlertCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    alert = Alert(**payload.model_dump(), tenant_id=current_user.tenant_id, created_by=current_user.id)
    db.add(alert)
    await db.flush()
    result = await db.execute(
        select(Alert)
        .options(selectinload(Alert.animal), selectinload(Alert.device))
        .where(Alert.id == alert.id)
    )
    return _serialize(result.scalar_one())


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert)
        .options(selectinload(Alert.animal), selectinload(Alert.device))
        .where(Alert.id == alert_id, Alert.tenant_id == current_user.tenant_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alerta no encontrada")
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.updated_by = current_user.id
    await db.flush()
    return _serialize(alert)


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert)
        .options(selectinload(Alert.animal), selectinload(Alert.device))
        .where(Alert.id == alert_id, Alert.tenant_id == current_user.tenant_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alerta no encontrada")
    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolved_by = current_user.id
    await db.flush()
    return _serialize(alert)


class DeviceEventPayload(BaseModel):
    dev_addr: str
    event: str  # offline | online | low_battery
    battery_pct: float | None = None


@router.post("/device-event")
async def device_event(
    payload: DeviceEventPayload,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Crea o resuelve alertas automaticamente desde eventos de dispositivos LoRa."""
    # Buscar si ya existe una alerta abierta del mismo tipo para este device_uid
    event_type = {
        "offline": AlertType.DEVICE_OFFLINE,
        "low_battery": AlertType.LOW_BATTERY,
    }.get(payload.event)

    if not event_type and payload.event not in ("online",):
        raise HTTPException(400, f"Evento desconocido: {payload.event}")

    if payload.event == "online":
        # Resolver alertas offline abiertas para este dispositivo
        result = await db.execute(
            select(Alert).where(
                Alert.tenant_id == current_user.tenant_id,
                Alert.alert_type == AlertType.DEVICE_OFFLINE,
                Alert.status == AlertStatus.OPEN,
                Alert.title.ilike(f"%{payload.dev_addr}%"),
            )
        )
        for alert in result.scalars().all():
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now(timezone.utc)
        await db.commit()
        return {"ok": True, "resolved_offline": True}

    if event_type:
        # Ver si ya existe alerta abierta
        result = await db.execute(
            select(Alert).where(
                Alert.tenant_id == current_user.tenant_id,
                Alert.alert_type == event_type,
                Alert.status == AlertStatus.OPEN,
                Alert.title.ilike(f"%{payload.dev_addr}%"),
            )
        )
        if result.scalar_one_or_none():
            return {"ok": True, "already_exists": True}

        title = f"{'Batería baja' if event_type == AlertType.LOW_BATTERY else 'Dispositivo offline'}: {payload.dev_addr}"
        msg = (
            f"Batería al {payload.battery_pct:.0f}%"
            if event_type == AlertType.LOW_BATTERY and payload.battery_pct is not None
            else f"El dispositivo {payload.dev_addr} dejó de transmitir."
        )
        alert = Alert(
            tenant_id=current_user.tenant_id,
            alert_type=event_type,
            severity=AlertSeverity.WARNING if event_type == AlertType.LOW_BATTERY else AlertSeverity.CRITICAL,
            title=title,
            message=msg,
            created_by=current_user.id,
        )
        db.add(alert)
        await db.commit()
        return {"ok": True, "created": True}

    return {"ok": True}


@router.get("/stats/summary")
async def alert_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert.severity, func.count(Alert.id))
        .where(Alert.tenant_id == current_user.tenant_id, Alert.status == AlertStatus.OPEN)
        .group_by(Alert.severity)
    )
    rows = result.all()
    return {row[0].value: row[1] for row in rows}
