from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.alert import AlertType, AlertSeverity, CONFIGURABLE_ALERT_TYPES
from app.models.alert_config import AlertConfig
from app.schemas.alert_config import AlertConfigResponse, AlertConfigCreate, AlertConfigUpdate
import uuid

router = APIRouter(prefix="/alert-configs", tags=["alert-configs"])


# Configuraciones por defecto que se crean para cada tenant nuevo o cuando no existen
DEFAULT_CONFIGS = [
    {
        "alert_type": AlertType.TEMPERATURE_LOW,
        "severity": AlertSeverity.CRITICAL,
        "threshold_min": 0.0,
        "repeat_interval_minutes": 240,
        "browser_notify": True,
        "name": "Temperatura baja",
    },
    {
        "alert_type": AlertType.TEMPERATURE_HIGH,
        "severity": AlertSeverity.CRITICAL,
        "threshold_max": 40.0,
        "repeat_interval_minutes": 240,
        "browser_notify": True,
        "name": "Temperatura alta",
    },
    {
        "alert_type": AlertType.LOW_BATTERY,
        "severity": AlertSeverity.WARNING,
        "threshold_value": 20.0,
        "repeat_interval_minutes": 1440,
        "browser_notify": True,
        "name": "Batería baja",
    },
    {
        "alert_type": AlertType.DEVICE_OFFLINE,
        "severity": AlertSeverity.WARNING,
        "threshold_value": None,
        "repeat_interval_minutes": 0,
        "browser_notify": False,
        "name": "Dispositivo offline",
    },
    {
        "alert_type": AlertType.PROLONGED_DISCONNECT,
        "severity": AlertSeverity.CRITICAL,
        "threshold_value": 60.0,
        "repeat_interval_minutes": 60,
        "browser_notify": True,
        "name": "Desconexión prolongada",
    },
    {
        "alert_type": AlertType.OUTSIDE_GEOFENCE,
        "severity": AlertSeverity.WARNING,
        "repeat_interval_minutes": 0,
        "browser_notify": True,
        "name": "Fuera de geocerca",
    },
    {
        "alert_type": AlertType.OUTSIDE_FIELD,
        "severity": AlertSeverity.CRITICAL,
        "repeat_interval_minutes": 0,
        "browser_notify": True,
        "name": "Fuera de campo",
    },
]


async def _ensure_defaults(tenant_id: uuid.UUID, db: AsyncSession) -> None:
    """Crea las configuraciones por defecto que falten para el tenant."""
    result = await db.execute(
        select(AlertConfig.alert_type).where(AlertConfig.tenant_id == tenant_id)
    )
    existing = {row[0] for row in result.all()}

    created = False
    for cfg in DEFAULT_CONFIGS:
        if cfg["alert_type"] in existing:
            continue
        db.add(
            AlertConfig(
                tenant_id=tenant_id,
                created_by=None,
                **cfg,
            )
        )
        created = True
    if created:
        await db.flush()


@router.get("", response_model=list[AlertConfigResponse])
async def list_alert_configs(
    ensure_defaults: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    tid = current_user.tenant_id
    if ensure_defaults:
        await _ensure_defaults(tid, db)
    result = await db.execute(
        select(AlertConfig)
        .where(AlertConfig.tenant_id == tid)
        .order_by(AlertConfig.alert_type)
    )
    return list(result.scalars().all())


@router.post("/seed-defaults", response_model=list[AlertConfigResponse])
async def seed_defaults(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Fuerza la (re)creación de las configuraciones por defecto faltantes."""
    await _ensure_defaults(current_user.tenant_id, db)
    result = await db.execute(
        select(AlertConfig)
        .where(AlertConfig.tenant_id == current_user.tenant_id)
        .order_by(AlertConfig.alert_type)
    )
    return list(result.scalars().all())


@router.post("", response_model=AlertConfigResponse, status_code=201)
async def create_alert_config(
    payload: AlertConfigCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.alert_type not in CONFIGURABLE_ALERT_TYPES:
        raise HTTPException(400, f"Tipo de alerta no configurable: {payload.alert_type}")
    exists = await db.execute(
        select(AlertConfig).where(
            AlertConfig.tenant_id == current_user.tenant_id,
            AlertConfig.alert_type == payload.alert_type,
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(409, "Ya existe una configuración para este tipo de alerta")
    cfg = AlertConfig(**payload.model_dump(), tenant_id=current_user.tenant_id, created_by=current_user.id)
    db.add(cfg)
    await db.flush()
    result = await db.execute(select(AlertConfig).where(AlertConfig.id == cfg.id))
    return result.scalar_one()


@router.put("/{config_id}", response_model=AlertConfigResponse)
async def update_alert_config(
    config_id: uuid.UUID,
    payload: AlertConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AlertConfig).where(
            AlertConfig.id == config_id,
            AlertConfig.tenant_id == current_user.tenant_id,
        )
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(404, "Configuración no encontrada")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(cfg, k, v)
    cfg.updated_by = current_user.id
    await db.flush()
    return cfg


@router.delete("/{config_id}", status_code=204)
async def delete_alert_config(
    config_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AlertConfig).where(
            AlertConfig.id == config_id,
            AlertConfig.tenant_id == current_user.tenant_id,
        )
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(404, "Configuración no encontrada")
    await db.delete(cfg)
