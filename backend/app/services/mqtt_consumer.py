import asyncio
import json
import logging
from datetime import datetime, timezone
import aiomqtt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.device import Device
from app.models.animal import Animal
from app.models.location import Location
from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

logger = logging.getLogger(__name__)

TOPIC_LOCATION = "exalink/+/devices/+/location"
TOPIC_STATUS = "exalink/+/devices/+/status"


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

    # Low battery alert
    battery = payload.get("battery")
    if battery is not None and battery <= 15:
        existing = await db.execute(
            select(Alert).where(
                Alert.device_id == device.id,
                Alert.alert_type == AlertType.LOW_BATTERY,
                Alert.status == AlertStatus.OPEN,
            )
        )
        if not existing.scalar_one_or_none():
            alert = Alert(
                tenant_id=device.tenant_id,
                device_id=device.id,
                animal_id=device.animal_id,
                alert_type=AlertType.LOW_BATTERY,
                severity=AlertSeverity.WARNING,
                title=f"Batería baja: {device.device_uid} ({battery}%)",
                message=f"El dispositivo {device.device_uid} tiene {battery}% de batería.",
                created_by=None,
            )
            db.add(alert)

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
