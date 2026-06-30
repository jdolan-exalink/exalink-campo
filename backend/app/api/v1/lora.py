import asyncio
from datetime import datetime, timezone
import os
import sqlite3
import time
from sqlalchemy import select, text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import to_shape
from shapely.geometry import Point
from app.core.database import get_db
from app.models.establishment import Establishment
from app.models.paddock import Paddock
from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus
from fastapi import APIRouter, Query, Body, Depends
from fastapi.responses import StreamingResponse
from app.core.config import settings

router = APIRouter(prefix="/lora", tags=["lora"])


async def _classify_lora_device_zone(db: AsyncSession, dev_addr: str, lat: float | None, lon: float | None, battery: float | None):
    if lat is None or lon is None:
        return None
    point = Point(lon, lat)
    est_result = await db.execute(select(Establishment).where(Establishment.is_active == True, Establishment.boundary.isnot(None)))
    establishments = est_result.scalars().all()
    field = None
    for est in establishments:
        if to_shape(est.boundary).covers(point):
            field = est
            break

    paddock = None
    if field:
        paddock_result = await db.execute(
            select(Paddock).where(Paddock.establishment_id == field.id, Paddock.is_active == True, Paddock.polygon.isnot(None))
        )
        for candidate in paddock_result.scalars().all():
            if to_shape(candidate.polygon).covers(point):
                paddock = candidate
                break

    tenant_id = field.tenant_id if field else (establishments[0].tenant_id if establishments else None)
    if tenant_id is None:
        return None

    field_id = field.id if field else None
    paddock_id = paddock.id if paddock else None
    last = await db.execute(
        sql_text("""
            SELECT field_id, paddock_id FROM device_zone_events
            WHERE dev_addr = :dev_addr
            ORDER BY created_at DESC LIMIT 1
        """),
        {"dev_addr": dev_addr},
    )
    row = last.first()
    changed = row is None or str(row.field_id) != str(field_id) or str(row.paddock_id) != str(paddock_id)
    if changed:
        event_type = "outside_field" if field is None else ("entered_paddock" if paddock else "inside_field")
        await db.execute(
            sql_text("""
                INSERT INTO device_zone_events
                  (tenant_id, dev_addr, field_id, field_name, paddock_id, paddock_name, lat, lon, event_type)
                VALUES (:tenant_id, :dev_addr, :field_id, :field_name, :paddock_id, :paddock_name, :lat, :lon, :event_type)
            """),
            {
                "tenant_id": tenant_id,
                "dev_addr": dev_addr,
                "field_id": field_id,
                "field_name": field.name if field else None,
                "paddock_id": paddock_id,
                "paddock_name": paddock.name if paddock else None,
                "lat": lat,
                "lon": lon,
                "event_type": event_type,
            },
        )

    if field is None:
        existing = await db.execute(
            select(Alert).where(
                Alert.tenant_id == tenant_id,
                Alert.status == AlertStatus.OPEN,
                Alert.alert_type == AlertType.OUTSIDE_GEOFENCE,
                Alert.title == f"Sensor fuera de campo: {dev_addr}",
            )
        )
        if existing.scalar_one_or_none() is None:
            db.add(Alert(
                tenant_id=tenant_id,
                alert_type=AlertType.OUTSIDE_GEOFENCE,
                severity=AlertSeverity.CRITICAL,
                title=f"Sensor fuera de campo: {dev_addr}",
                message=f"El sensor {dev_addr} esta fuera de todos los campos registrados. Coordenadas: {lat:.6f}, {lon:.6f}. Bateria: {battery if battery is not None else 'N/D'}%.",
            ))
    else:
        alerts = await db.execute(
            select(Alert).where(
                Alert.tenant_id == tenant_id,
                Alert.status == AlertStatus.OPEN,
                Alert.alert_type == AlertType.OUTSIDE_GEOFENCE,
                Alert.title == f"Sensor fuera de campo: {dev_addr}",
            )
        )
        for alert in alerts.scalars().all():
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now(timezone.utc)

    return {
        "field_id": str(field.id) if field else None,
        "field_name": field.name if field else None,
        "paddock_id": str(paddock.id) if paddock else None,
        "paddock_name": paddock.name if paddock else None,
        "outside_field": field is None,
    }


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.LORA_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_lora_schema() -> None:
    """Asegura que el SQLite local tenga todas las columnas usadas por los endpoints.

    Como este servicio comparte DB con el Flask listener en producción pero
    ambos pueden inicializar la DB, mantenemos un ALTER TABLE defensivo.
    """
    try:
        os.makedirs(os.path.dirname(settings.LORA_DB_PATH), exist_ok=True)
    except Exception:
        pass
    conn = _get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS packets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                gateway_id  TEXT    NOT NULL,
                received_at REAL,
                rssi        INTEGER,
                snr         REAL,
                freq_mhz    REAL,
                sf          INTEGER,
                payload_hex TEXT,
                dev_addr    TEXT,
                temperature REAL,
                humidity    REAL,
                battery     REAL,
                charging    INTEGER,
                wake_boots  INTEGER,
                wake_time_ms INTEGER,
                mtype_str   TEXT,
                fcnt        INTEGER,
                lat         REAL,
                lon         REAL,
                a0x REAL, a0y REAL, a0z REAL,
                a1x REAL, a1y REAL, a1z REAL,
                created_at  TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS gateways (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                gateway_id  TEXT NOT NULL UNIQUE,
                name        TEXT,
                lat         REAL,
                lon         REAL,
                wifi_ssid   TEXT,
                wifi_rssi   INTEGER,
                battery_pct REAL,
                charging    INTEGER DEFAULT 0,
                temperature REAL,
                humidity    REAL,
                uptime_s    INTEGER,
                pkts_total  INTEGER,
                location    TEXT,
                last_seen   TIMESTAMP,
                updated_at  TIMESTAMP,
                is_active   INTEGER DEFAULT 1,
                notes       TEXT,
                created_at  TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS devices (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                dev_addr       TEXT NOT NULL UNIQUE,
                name           TEXT,
                dev_eui        TEXT,
                device_type    TEXT DEFAULT 'sensor',
                gateway_id     TEXT,
                refresh_freq_s INTEGER DEFAULT 60,
                hw_version     TEXT,
                lat            REAL,
                lon            REAL,
                wifi_ssid      TEXT,
                wifi_rssi      INTEGER,
                battery_pct    REAL,
                temperature    REAL,
                humidity       REAL,
                charging       INTEGER DEFAULT 0,
                is_paired      INTEGER DEFAULT 0,
                pairing_code   TEXT,
                pairing_expires_at TIMESTAMP,
                a0x REAL, a0y REAL, a0z REAL,
                a1x REAL, a1y REAL, a1z REAL,
                last_seen      TIMESTAMP,
                updated_at     TIMESTAMP,
                is_active      INTEGER DEFAULT 1,
                notes          TEXT,
                created_at     TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS config (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_packets_created_at ON packets(created_at);
            CREATE INDEX IF NOT EXISTS idx_packets_gateway    ON packets(gateway_id);
            CREATE INDEX IF NOT EXISTS idx_packets_dev_addr   ON packets(dev_addr);
        """)

        # Migraciones defensivas para tablas pre-existentes
        for tbl, cols in [
            ("gateways", [
                ("is_paired",          "INTEGER DEFAULT 0"),
                ("pairing_code",       "TEXT"),
                ("pairing_expires_at", "TIMESTAMP"),
                ("wifi_ip",            "TEXT"),
                ("charging",           "INTEGER DEFAULT 0"),
                ("temperature",        "REAL"),
                ("humidity",           "REAL"),
            ]),
            ("packets", [
                ("battery",      "REAL"),
                ("charging",     "INTEGER"),
                ("wake_boots",   "INTEGER"),
                ("wake_time_ms", "INTEGER"),
                ("lat", "REAL"), ("lon", "REAL"),
                ("a0x", "REAL"), ("a0y", "REAL"), ("a0z", "REAL"),
                ("a1x", "REAL"), ("a1y", "REAL"), ("a1z", "REAL"),
            ]),
            ("devices", [
                ("temperature",         "REAL"),
                ("charging",            "INTEGER DEFAULT 0"),
                ("is_paired",           "INTEGER DEFAULT 0"),
                ("pairing_code",        "TEXT"),
                ("pairing_expires_at",  "TIMESTAMP"),
                ("a0x", "REAL"), ("a0y", "REAL"), ("a0z", "REAL"),
                ("a1x", "REAL"), ("a1y", "REAL"), ("a1z", "REAL"),
            ]),
        ]:
            existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({tbl})").fetchall()}
            for col, decl in cols:
                if col not in existing:
                    conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {decl}")
                    print(f"[LoraDB] Columna agregada: {tbl}.{col}")

        conn.commit()
    except Exception as e:
        print(f"[LoraDB] WARNING: no se pudo asegurar schema: {e}")
    finally:
        conn.close()


_ensure_lora_schema()


# ── Ingest (recibe paquetes del GW) ─────────────────────────────

@router.post("/ingest")
async def ingest(payload: dict = Body(...)):
    gw_id = payload.get("gateway_id", "?")
    payload_hex = payload.get("payload_hex", "")
    payload_json = payload.get("payload_json")

    conn = _get_db()
    try:
        # Decode JSON payload
        data = None
        if payload_json:
            try:
                import json as _json
                data = _json.loads(payload_json) if isinstance(payload_json, str) else payload_json
            except Exception:
                data = None
        if data is None and payload_hex:
            try:
                raw = bytes.fromhex(payload_hex)
                text = raw.decode("utf-8")
                import json as _json
                data = _json.loads(text)
            except Exception:
                data = None

        dev_addr = None
        temperature = humidity = battery = charging = None
        wake_boots = wake_time_ms = None
        lat = lon = None
        a0x = a0y = a0z = a1x = a1y = a1z = None

        if isinstance(data, dict):
            dev_addr = data.get("d")
            battery = data.get("b")
            if battery is None:
                battery = data.get("battery_pct")
            temp = data.get("t")
            if temp is None:
                temp = data.get("temperature")
            temperature = temp
            hum = data.get("h")
            if hum is None:
                hum = data.get("humidity")
            humidity = hum
            charging = data.get("ch")
            wake_boots = data.get("wb")
            wake_time_ms = data.get("wt")
            lat = data.get("lt")
            lon = data.get("ln")
            # Accelerometer
            def _sf(v):
                try:
                    return float(v) if v is not None else None
                except (ValueError, TypeError):
                    return None
            a0x = _sf(data.get("a0x"))
            a0y = _sf(data.get("a0y"))
            a0z = _sf(data.get("a0z"))
            a1x = _sf(data.get("a1x"))
            a1y = _sf(data.get("a1y"))
            a1z = _sf(data.get("a1z"))

        if not dev_addr and payload_hex:
            dev_addr = "raw-" + payload_hex[:8]

        # Store packet
        conn.execute("""
            INSERT INTO packets
              (gateway_id, received_at, rssi, snr, freq_mhz, sf,
               payload_hex, dev_addr, temperature, humidity, battery, charging,
               wake_boots, wake_time_ms, mtype_str, fcnt,
               lat, lon,
               a0x, a0y, a0z, a1x, a1y, a1z, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
        """, (
            gw_id,
            payload.get("received_at", 0),
            payload.get("rssi"),
            payload.get("snr"),
            payload.get("freq_mhz"),
            payload.get("sf"),
            payload_hex,
            dev_addr,
            temperature,
            humidity,
            battery,
            charging,
            wake_boots,
            wake_time_ms,
            (payload.get("lorawan") or {}).get("mtype_str"),
            (payload.get("lorawan") or {}).get("fcnt"),
            lat, lon,
            a0x, a0y, a0z, a1x, a1y, a1z,
        ))

        # Auto-register gateway
        conn.execute(
            "INSERT OR IGNORE INTO gateways (gateway_id, last_seen) VALUES (?, datetime('now', 'localtime'))",
            (gw_id,),
        )
        conn.execute(
            "UPDATE gateways SET last_seen = datetime('now', 'localtime') WHERE gateway_id = ?",
            (gw_id,),
        )

        # Auto-register device
        if dev_addr:
            conn.execute(
                "INSERT OR IGNORE INTO devices (dev_addr, last_seen) VALUES (?, datetime('now', 'localtime'))",
                (dev_addr,),
            )
            # Update device latest values
            updates = ["last_seen = datetime('now', 'localtime')"]
            params = []
            if data and data.get("lt") is not None:
                updates.append("lat = ?"); params.append(data["lt"])
            if data and data.get("ln") is not None:
                updates.append("lon = ?"); params.append(data["ln"])
            if battery is not None:
                updates.append("battery_pct = ?"); params.append(battery)
            if temperature is not None:
                updates.append("temperature = ?"); params.append(temperature)
            if humidity is not None:
                updates.append("humidity = ?"); params.append(humidity)
            if a0x is not None: updates.append("a0x = ?"); params.append(a0x)
            if a0y is not None: updates.append("a0y = ?"); params.append(a0y)
            if a0z is not None: updates.append("a0z = ?"); params.append(a0z)
            if a1x is not None: updates.append("a1x = ?"); params.append(a1x)
            if a1y is not None: updates.append("a1y = ?"); params.append(a1y)
            if a1z is not None: updates.append("a1z = ?"); params.append(a1z)
            # Pairing code
            if data and data.get("pc"):
                pairing_code = data["pc"]
                existing_paired = conn.execute(
                    "SELECT is_paired FROM devices WHERE dev_addr = ?", (dev_addr,)
                ).fetchone()
                is_already_paired = existing_paired and existing_paired["is_paired"]
                if not is_already_paired:
                    updates.append("pairing_code = ?"); params.append(pairing_code)
                    updates.append("pairing_expires_at = datetime('now', 'localtime', '+10 minutes')")
            conn.execute(
                f"UPDATE devices SET {', '.join(updates)} WHERE dev_addr = ?",
                params + [dev_addr],
            )

        conn.commit()
        print(f"[INGEST] GW={gw_id} Dev={dev_addr} bat={battery}% temp={temperature}")
        return {"ok": True}
    except Exception as e:
        print(f"[INGEST] ERROR: {e}")
        return {"ok": False, "msg": str(e)}, 500
    finally:
        conn.close()


# ── Packets ────────────────────────────────────────────────────────

@router.get("/packets")
async def get_packets(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    gateway: str | None = Query(None),
    dev: str | None = Query(None),
    mtype: str | None = Query(None),
):
    where = []
    params = []
    if gateway:
        where.append("p.gateway_id = ?")
        params.append(gateway)
    if dev:
        where.append("p.dev_addr = ?")
        params.append(dev)
    if mtype:
        where.append("p.mtype_str = ?")
        params.append(mtype)

    sql = ("SELECT p.*, g.name AS gateway_name, d.name AS device_name "
           "FROM packets p "
           "LEFT JOIN gateways g ON p.gateway_id = g.gateway_id "
           "LEFT JOIN devices d ON p.dev_addr = d.dev_addr")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY p.id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    try:
        conn = _get_db()
        rows = conn.execute(sql, params).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM packets"
            + (" WHERE " + " AND ".join(where) if where else ""),
            params[:-2] if where else [],
        ).fetchone()[0]
        conn.close()
        return {"count": total, "limit": limit, "offset": offset, "packets": [dict(r) for r in rows]}
    except Exception:
        return {"count": 0, "limit": limit, "offset": offset, "packets": []}


# ── Stats ──────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats():
    try:
        conn = _get_db()
        total = conn.execute("SELECT COUNT(*) FROM packets").fetchone()[0]
        last = conn.execute("SELECT * FROM packets ORDER BY id DESC LIMIT 1").fetchone()
        gw_registered = conn.execute("SELECT COUNT(*) FROM gateways WHERE COALESCE(is_paired, 0) = 1").fetchone()[0]
        dev_registered = conn.execute("SELECT COUNT(*) FROM devices WHERE COALESCE(is_paired, 0) = 1").fetchone()[0]
        conn.close()
        return {
            "total_packets": total,
            "gateways_registered": gw_registered,
            "devices_registered": dev_registered,
            "last_packet": dict(last) if last else None,
        }
    except Exception:
        return {"total_packets": 0, "gateways_registered": 0,
                "devices_registered": 0, "last_packet": None}


# ── Gateways ───────────────────────────────────────────────────────

@router.get("/gateways")
async def get_gateways(include_pending: bool = Query(False)):
    try:
        conn = _get_db()
        where = ""
        if not include_pending:
            where = "WHERE g.is_paired = 1"
        rows = conn.execute(f"""
            SELECT g.*, p.total_packets, COALESCE(dc.device_count, 0) AS device_count,
                   CASE WHEN g.last_seen IS NOT NULL AND g.last_seen > datetime('now', 'localtime', '-1 hours') THEN 1 ELSE 0 END AS online
            FROM gateways g
            LEFT JOIN (
                SELECT gateway_id, COUNT(*) AS total_packets FROM packets GROUP BY gateway_id
            ) p ON g.gateway_id = p.gateway_id
            LEFT JOIN (
                SELECT gateway_id, COUNT(DISTINCT dev_addr) AS device_count FROM packets WHERE dev_addr IS NOT NULL GROUP BY gateway_id
            ) dc ON g.gateway_id = dc.gateway_id
            {where}
            ORDER BY g.last_seen DESC NULLS LAST
        """).fetchall()
        conn.close()
        return {"gateways": [dict(r) for r in rows]}
    except Exception:
        return {"gateways": []}


@router.get("/gateways/pending")
async def get_pending_gateways():
    try:
        conn = _get_db()
        rows = conn.execute("""
            SELECT g.gateway_id, g.pairing_expires_at, g.last_seen, g.updated_at,
                   g.lat, g.lon, g.wifi_ssid, g.wifi_rssi, g.battery_pct,
                   g.uptime_s, g.pkts_total, g.is_paired
            FROM gateways g
            WHERE COALESCE(g.is_paired, 0) = 0
              AND g.pairing_code IS NOT NULL
              AND g.pairing_expires_at IS NOT NULL
              AND g.pairing_expires_at > datetime('now', 'localtime')
            ORDER BY g.pairing_expires_at ASC
        """).fetchall()
        conn.close()
        return {"gateways": [dict(r) for r in rows]}
    except Exception:
        return {"gateways": []}


@router.post("/gateways/pair")
async def pair_gateway(payload: dict = Body(...)):
    try:
        code = (payload.get("pairing_code") or "").strip()
        name = (payload.get("name") or "").strip()
        hint_gw_id = (payload.get("gateway_id") or "").strip() or None

        if not code:
            return {"ok": False, "msg": "pairing_code requerido"}

        conn = _get_db()

        # Buscar por código primero (más confiable — el GW regenera códigos)
        row = conn.execute(
            "SELECT gateway_id, pairing_code, pairing_expires_at, is_paired, name "
            "FROM gateways WHERE pairing_code = ? AND COALESCE(is_paired, 0) = 0 "
            "AND pairing_expires_at IS NOT NULL AND pairing_expires_at > datetime('now', 'localtime') "
            "ORDER BY pairing_expires_at DESC LIMIT 1",
            (code,),
        ).fetchone()

        # Si no encontró por código pero el usuario dio un gateway_id,
        # verificar si ese GW tiene el código (podría haber regenerado)
        if not row and hint_gw_id:
            row = conn.execute(
                "SELECT gateway_id, pairing_code, pairing_expires_at, is_paired, name "
                "FROM gateways WHERE gateway_id = ?",
                (hint_gw_id,),
            ).fetchone()
            if row and (row["pairing_code"] or "") != code:
                conn.close()
                return {"ok": False, "msg": "El codigo no corresponde a este gateway. Verifica el codigo en la pantalla OLED."}

        if not row:
            conn.close()
            return {"ok": False, "msg": "Codigo de pairing invalido o expirado. Verifica que el gateway este conectado y el codigo vigente."}

        if row["is_paired"]:
            conn.close()
            return {"ok": False, "msg": "El gateway ya esta registrado."}

        gw_id = row["gateway_id"]
        final_name = name if name else gw_id   # auto-asignar ID si no hay nombre

        conn.execute(
            """
            UPDATE gateways
               SET is_paired = 1,
                   name = ?,
                   pairing_code = NULL,
                   pairing_expires_at = NULL,
                   updated_at = CURRENT_TIMESTAMP,
                   last_seen = CURRENT_TIMESTAMP
             WHERE gateway_id = ?
            """,
            (final_name, gw_id),
        )
        conn.commit()
        conn.close()
        return {"ok": True, "gateway_id": gw_id, "name": final_name}
    except Exception as e:
        return {"ok": False, "msg": f"Error al emparejar: {e}"}


@router.post("/gateways")
async def create_gateway(payload: dict = Body(...)):
    try:
        conn = _get_db()
        conn.execute(
            "INSERT INTO gateways (gateway_id, name, location, notes) VALUES (?, ?, ?, ?)",
            (payload.get("gateway_id", ""), payload.get("name", ""),
             payload.get("location", ""), payload.get("notes", "")),
        )
        conn.commit()
        conn.close()
        return {"ok": True}
    except sqlite3.IntegrityError:
        return {"ok": False, "msg": "Gateway ID ya existe"}
    except Exception:
        return {"ok": False, "msg": "Error al crear gateway"}


@router.put("/gateways/{gateway_id}")
async def update_gateway(gateway_id: str, payload: dict = Body(...)):
    try:
        conn = _get_db()
        updates = []
        params = []
        for key, col in {"name": "name", "location": "location", "notes": "notes", "lat": "lat", "lon": "lon"}.items():
            if key in payload and payload[key] is not None:
                updates.append(f"{col} = ?")
                params.append(payload[key])
        if updates:
            conn.execute(
                f"UPDATE gateways SET {', '.join(updates)} WHERE gateway_id=?",
                params + [gateway_id],
            )
        conn.commit()
        conn.close()
        return {"ok": True}
    except Exception:
        return {"ok": False, "msg": "Error al actualizar gateway"}


@router.delete("/gateways/{gateway_id}")
async def delete_gateway(gateway_id: str):
    try:
        conn = _get_db()
        conn.execute("DELETE FROM gateways WHERE gateway_id=?", (gateway_id,))
        conn.commit()
        conn.close()
        return {"ok": True}
    except Exception:
        return {"ok": False, "msg": "Error al eliminar gateway"}


@router.post("/gateway/sync")
async def sync_gateway(payload: dict = Body(...), db: AsyncSession = Depends(get_db)):
    try:
        gw_id = payload.get("gateway_id")
        if not gw_id:
            return {"ok": False, "msg": "gateway_id requerido"}

        conn = _get_db()
        conn.execute("INSERT OR IGNORE INTO gateways (gateway_id) VALUES (?)", (gw_id,))

        updates = ["updated_at = CURRENT_TIMESTAMP", "last_seen = CURRENT_TIMESTAMP"]
        params = []
        field_map = {
            "name": "name", "lat": "lat", "lon": "lon",
            "wifi_ssid": "wifi_ssid", "wifi_rssi": "wifi_rssi",
            "battery_pct": "battery_pct", "charging": "charging",
            "temperature": "temperature", "humidity": "humidity",
            "uptime_s": "uptime_s",
            "pkts_total": "pkts_total",
            # is_paired NO se actualiza desde sync — solo el endpoint /pair lo cambia
        }
        for json_key, col in field_map.items():
            if json_key in payload and payload[json_key] is not None:
                updates.append(f"{col} = ?")
                params.append(payload[json_key])

        # pairing_code y expiry sólo si viene y el GW NO está paired en la DB
        existing_paired = conn.execute(
            "SELECT is_paired FROM gateways WHERE gateway_id = ?", (gw_id,)
        ).fetchone()
        is_already_paired = existing_paired and existing_paired["is_paired"]
        if payload.get("pairing_code") and not is_already_paired:
            updates.append("pairing_code = ?")
            params.append(payload["pairing_code"])
            if payload.get("pairing_expires_at"):
                updates.append("pairing_expires_at = datetime(?, 'unixepoch')")
                params.append(int(payload["pairing_expires_at"]))

        conn.execute(f"UPDATE gateways SET {', '.join(updates)} WHERE gateway_id = ?", params + [gw_id])

        # Guardar lectura de sensores del GW como packet para historial
        # (throttle: solo si la ultima lectura del GW es > 5 min)
        gw_dev = f"gw:{gw_id}"
        last_gw_pkt = conn.execute(
            "SELECT created_at FROM packets WHERE dev_addr = ? ORDER BY id DESC LIMIT 1",
            (gw_dev,),
        ).fetchone()
        should_store = True
        if last_gw_pkt:
            age = conn.execute(
                "SELECT (julianday('now','localtime') - julianday(created_at)) * 1440 FROM packets WHERE id = (SELECT MAX(id) FROM packets WHERE dev_addr = ?)",
                (gw_dev,),
            ).fetchone()[0]
            if age is not None and age < 5:
                should_store = False

        if should_store:
            conn.execute("""
                INSERT INTO packets
                  (gateway_id, received_at, rssi, snr, freq_mhz, sf,
                   payload_hex, dev_addr, temperature, humidity, battery, charging,
                   wake_boots, wake_time_ms, mtype_str, fcnt, created_at)
                VALUES (?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """, (
                gw_id,
                int(payload.get("uptime_s", 0)),
                payload.get("wifi_rssi"),
                None,
                None,
                None,
                gw_dev,
                payload.get("temperature"),
                payload.get("humidity"),
                payload.get("battery_pct"),
                payload.get("charging"),
                None, None, "GW_SYNC", None,
            ))

        conn.commit()
        row = conn.execute(
            "SELECT name, is_paired FROM gateways WHERE gateway_id = ?", (gw_id,)
        ).fetchone()

        # Dispositivos paired que el GW debe provisionar via LoRa downlink
        provision_devices = [
            r["dev_addr"] for r in conn.execute(
                "SELECT dev_addr FROM devices WHERE COALESCE(is_paired, 0) = 1"
            ).fetchall()
        ]

        conn.close()

        # Check provisioning status in PostgreSQL (non-critical — si falla, devolvemos False)
        is_provisioned = False
        try:
            from app.models.device import Device as PgDevice
            pg_device = await db.scalar(
                select(PgDevice).where(PgDevice.device_uid == gw_id)
            )
            is_provisioned = pg_device.is_provisioned if pg_device else False
        except Exception as e:
            print(f"[LoraSync] WARN: PostgreSQL query falló (no crítico): {e}")

        return {
            "ok": True,
            "name": row["name"] if row else None,
            "is_paired": bool(row["is_paired"]) if row else False,
            "is_provisioned": is_provisioned,
            "provision_devices": provision_devices,
        }
    except Exception as e:
        print(f"[LoraSync] ERROR sync_gateway: {e}")
        import traceback
        traceback.print_exc()
        return {"ok": False, "msg": "Error al sincronizar gateway"}


# ── Devices ────────────────────────────────────────────────────────

@router.get("/devices")
async def get_devices(db: AsyncSession = Depends(get_db)):
    try:
        conn = _get_db()
        rows = conn.execute("""
            SELECT d.*, p.total_packets,
                   CASE
                     WHEN d.last_seen IS NULL THEN 0
                     WHEN d.last_seen > datetime('now', 'localtime', '-' || MAX(COALESCE(d.refresh_freq_s, 60), 300) || ' seconds') THEN 1
                     WHEN d.last_seen > datetime('now', 'localtime', '-' || (MAX(COALESCE(d.refresh_freq_s, 60), 300) * 3) || ' seconds') THEN 2
                     ELSE 0
                   END AS online
            FROM devices d
            LEFT JOIN (
                SELECT dev_addr, COUNT(*) AS total_packets FROM packets GROUP BY dev_addr
            ) p ON d.dev_addr = p.dev_addr
            WHERE COALESCE(d.is_paired, 0) = 1
            ORDER BY d.last_seen DESC NULLS LAST
        """).fetchall()
        conn.close()
        devices = []
        for r in rows:
            item = dict(r)
            zone = await _classify_lora_device_zone(
                db, item.get("dev_addr"), item.get("lat"), item.get("lon"), item.get("battery_pct")
            )
            if zone:
                item.update(zone)
            devices.append(item)
        return {"devices": devices}
    except Exception:
        return {"devices": []}


@router.get("/devices/{dev_addr}/available-days")
async def get_device_available_days(dev_addr: str):
    try:
        conn = _get_db()
        rows = conn.execute(
            "SELECT DISTINCT date(created_at) as day FROM packets WHERE dev_addr = ? ORDER BY day DESC LIMIT 90",
            (dev_addr,),
        ).fetchall()
        conn.close()
        return {"days": [r["day"] for r in rows]}
    except Exception:
        return {"days": []}


@router.get("/devices/{dev_addr}/sensor-history")
async def get_device_sensor_history(
    dev_addr: str,
    limit: int = Query(500, ge=1, le=2000),
    date: str = Query(None, description="YYYY-MM-DD para filtrar un dia especifico"),
):
    try:
        conn = _get_db()
        if date:
            rows = conn.execute(
                """
                SELECT created_at, temperature, humidity, battery,
                       lat, lon, rssi, snr
                FROM packets
                WHERE dev_addr = ?
                  AND date(created_at) = date(?)
                ORDER BY created_at ASC
                """,
                (dev_addr, date),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT created_at, temperature, humidity, battery,
                       lat, lon, rssi, snr
                FROM packets
                WHERE dev_addr = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (dev_addr, limit),
            ).fetchall()
            rows = list(reversed(rows))
        conn.close()

        # Agrupar por intervalos de ~10 minutos (tomar el promedio)
        buckets: dict[str, list] = {}
        for row in rows:
            ts = row["created_at"] or ""
            # bucket key: "YYYY-MM-DD HH:M0" (truncar minutos a decena)
            if len(ts) >= 16:
                minute = int(ts[14:16])
                bucket_minute = (minute // 10) * 10
                key = ts[:14] + f"{bucket_minute:02d}"
            else:
                key = ts

            if key not in buckets:
                buckets[key] = []
            buckets[key].append(row)

        points = []
        prev_lat, prev_lon = None, None
        for key in sorted(buckets.keys()):
            group = buckets[key]
            n = len(group)

            def avg(field):
                vals = [r[field] for r in group if r[field] is not None]
                return round(sum(vals) / len(vals), 1) if vals else None

            p = {"ts": key}
            t = avg("temperature")
            h = avg("humidity")
            b = avg("battery")
            if t is not None: p["t"] = t
            if h is not None: p["h"] = h
            if b is not None: p["b"] = b
            rssi = avg("rssi")
            if rssi is not None: p["rssi"] = rssi

            # GPS solo si hay movimiento (> ~15m ≈ 0.00014 grados)
            for r in group:
                if r["lat"] is not None and r["lon"] is not None:
                    cur_lat, cur_lon = r["lat"], r["lon"]
                    moved = (prev_lat is None or
                             abs(cur_lat - prev_lat) > 0.00014 or
                             abs(cur_lon - prev_lon) > 0.00014)
                    if moved:
                        p["lt"] = round(cur_lat, 6)
                        p["ln"] = round(cur_lon, 6)
                        prev_lat = cur_lat
                        prev_lon = cur_lon
                    break

            points.append(p)

        return {"dev_addr": dev_addr, "points": points}
    except Exception:
        return {"dev_addr": dev_addr, "points": []}


@router.get("/devices/{dev_addr}/temperature-history")
async def get_device_temperature_history(
    dev_addr: str,
    limit: int = Query(72, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    try:
        conn = _get_db()
        rows = conn.execute(
            """
            SELECT created_at, temperature
            FROM packets
            WHERE dev_addr = ? AND temperature IS NOT NULL
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (dev_addr, limit),
        ).fetchall()
        conn.close()
        points = [
            {"ts": row["created_at"], "temperature": row["temperature"]}
            for row in reversed(rows)
        ]
        return {"dev_addr": dev_addr, "points": points}
    except Exception:
        return {"dev_addr": dev_addr, "points": []}


@router.get("/devices/{dev_addr}/battery-history")
async def get_device_battery_history(
    dev_addr: str,
    limit: int = Query(72, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    try:
        conn = _get_db()
        rows = conn.execute(
            """
            SELECT created_at, battery
            FROM packets
            WHERE dev_addr = ? AND battery IS NOT NULL
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (dev_addr, limit),
        ).fetchall()
        conn.close()
        points = [
            {"ts": row["created_at"], "battery": row["battery"]}
            for row in reversed(rows)
        ]
        return {"dev_addr": dev_addr, "points": points}
    except Exception:
        return {"dev_addr": dev_addr, "points": []}


@router.get("/devices/{dev_addr}/accel-history")
async def get_device_accel_history(
    dev_addr: str,
    limit: int = Query(72, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    try:
        conn = _get_db()
        rows = conn.execute(
            """
            SELECT created_at, a0x, a0y, a0z, a1x, a1y, a1z
            FROM packets
            WHERE dev_addr = ?
              AND (a0x IS NOT NULL OR a1x IS NOT NULL)
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (dev_addr, limit),
        ).fetchall()
        conn.close()
        points = []
        for row in reversed(rows):
            p = {"ts": row["created_at"]}
            for k in ("a0x", "a0y", "a0z", "a1x", "a1y", "a1z"):
                if row[k] is not None:
                    p[k] = round(row[k], 3)
            points.append(p)
        return {"dev_addr": dev_addr, "points": points}
    except Exception:
        return {"dev_addr": dev_addr, "points": []}


I_ACTIVE_MA = 80.0
I_SLEEP_MA = 0.15
BATTERY_CAPACITY_MAH = 3000.0
TX_INTERVAL_MS = 300000


@router.get("/devices/{dev_addr}/consumption")
async def get_device_consumption(
    dev_addr: str,
    limit: int = Query(48, ge=1, le=288),
    db: AsyncSession = Depends(get_db),
):
    try:
        conn = _get_db()
        rows = conn.execute(
            """
            SELECT created_at, battery, charging, wake_boots, wake_time_ms
            FROM packets
            WHERE dev_addr = ? AND wake_time_ms IS NOT NULL
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (dev_addr, limit),
        ).fetchall()
        conn.close()

        if len(rows) < 2:
            return {"dev_addr": dev_addr, "samples": 0, "msg": "Datos insuficientes"}

        cycles = []
        brownouts = 0
        prev_wb = None
        for row in reversed(rows):
            wt = row["wake_time_ms"] or 0
            battery = row["battery"]
            charging = row["charging"]
            wb = row["wake_boots"]

            duty = min(wt / TX_INTERVAL_MS, 1.0)
            cycle_mah = (wt * I_ACTIVE_MA + (TX_INTERVAL_MS - wt) * I_SLEEP_MA) / 3_600_000
            cycles.append({
                "ts": row["created_at"],
                "battery": battery,
                "charging": charging,
                "wake_boots": wb,
                "wake_time_ms": wt,
                "duty_pct": round(duty * 100, 2),
                "cycle_mah": round(cycle_mah, 4),
            })

            if prev_wb is not None:
                wb_delta = wb - prev_wb if wb is not None and prev_wb is not None else 1
                if wb_delta > 1:
                    brownouts += 1
            prev_wb = wb

        avg_cycle_mah = sum(c["cycle_mah"] for c in cycles) / len(cycles)
        daily_mah = avg_cycle_mah * 288
        last_battery = cycles[-1]["battery"]
        autonomy_days = None
        if last_battery is not None and daily_mah > 0:
            autonomy_days = round((last_battery / 100) * BATTERY_CAPACITY_MAH / daily_mah, 1)

        return {
            "dev_addr": dev_addr,
            "samples": len(cycles),
            "avg_cycle_mah": round(avg_cycle_mah, 4),
            "daily_mah": round(daily_mah, 2),
            "autonomy_days": autonomy_days,
            "brownouts_detected": brownouts,
            "last_charging": cycles[-1]["charging"] if cycles else None,
            "cycles": cycles[-12:],
        }
    except Exception:
        return {"dev_addr": dev_addr, "samples": 0, "msg": "Error al calcular consumo"}


@router.get("/devices/pending")
async def get_pending_devices():
    try:
        conn = _get_db()
        rows = conn.execute("""
            SELECT d.dev_addr, d.name, d.device_type, d.pairing_code,
                   d.pairing_expires_at, d.last_seen, d.battery_pct,
                   d.temperature, d.created_at, d.is_paired
            FROM devices d
            WHERE COALESCE(d.is_paired, 0) = 0
              AND d.pairing_code IS NOT NULL
              AND d.pairing_expires_at IS NOT NULL
              AND d.pairing_expires_at > datetime('now', 'localtime')
            ORDER BY d.pairing_expires_at ASC
        """).fetchall()
        conn.close()
        return {"devices": [dict(r) for r in rows]}
    except Exception:
        return {"devices": []}


@router.post("/devices/pair")
async def pair_device(payload: dict = Body(...)):
    try:
        dev_addr = (payload.get("dev_addr") or "").strip()
        name = (payload.get("name") or "").strip()

        if not dev_addr:
            return {"ok": False, "msg": "dev_addr requerido"}

        conn = _get_db()
        row = conn.execute(
            "SELECT dev_addr, pairing_code, pairing_expires_at, is_paired, name "
            "FROM devices WHERE dev_addr = ?",
            (dev_addr,),
        ).fetchone()

        if not row:
            conn.close()
            return {"ok": False, "msg": "Dispositivo no encontrado"}

        if row["is_paired"]:
            conn.close()
            return {"ok": False, "msg": "El dispositivo ya esta registrado"}

        final_name = name if name else (row["name"] or dev_addr)

        conn.execute(
            """
            UPDATE devices
               SET is_paired = 1,
                   name = ?,
                   pairing_code = NULL,
                   pairing_expires_at = NULL,
                   updated_at = CURRENT_TIMESTAMP,
                   last_seen = CURRENT_TIMESTAMP
             WHERE dev_addr = ?
            """,
            (final_name, dev_addr),
        )
        conn.commit()
        conn.close()
        return {"ok": True, "dev_addr": dev_addr, "name": final_name}
    except Exception as e:
        return {"ok": False, "msg": f"Error al emparejar: {e}"}


@router.post("/devices")
async def create_device(payload: dict = Body(...)):
    try:
        conn = _get_db()
        conn.execute(
            "INSERT INTO devices (dev_addr, name, dev_eui, device_type, gateway_id, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (payload.get("dev_addr", ""), payload.get("name", ""),
             payload.get("dev_eui", ""), payload.get("device_type", "sensor"),
             payload.get("gateway_id", ""), payload.get("notes", "")),
        )
        conn.commit()
        conn.close()
        return {"ok": True}
    except sqlite3.IntegrityError:
        return {"ok": False, "msg": "DevAddr ya existe"}
    except Exception:
        return {"ok": False, "msg": "Error al crear dispositivo"}


@router.put("/devices/{dev_addr}")
async def update_device(dev_addr: str, payload: dict = Body(...)):
    try:
        conn = _get_db()
        updates = []
        params = []
        field_map = {
            "name": "name", "dev_eui": "dev_eui", "device_type": "device_type",
            "gateway_id": "gateway_id", "refresh_freq_s": "refresh_freq_s",
            "hw_version": "hw_version", "notes": "notes",
            "lat": "lat", "lon": "lon",
        }
        for key, col in field_map.items():
            if key in payload and payload[key] is not None:
                updates.append(f"{col} = ?")
                params.append(payload[key])
        if updates:
            conn.execute(f"UPDATE devices SET {', '.join(updates)} WHERE dev_addr=?", params + [dev_addr])
        conn.commit()
        conn.close()
        return {"ok": True}
    except Exception:
        return {"ok": False, "msg": "Error al actualizar dispositivo"}


@router.delete("/devices/{dev_addr}")
async def delete_device(dev_addr: str):
    try:
        conn = _get_db()
        conn.execute("DELETE FROM devices WHERE dev_addr=?", (dev_addr,))
        conn.commit()
        conn.close()
        return {"ok": True}
    except Exception:
        return {"ok": False, "msg": "Error al eliminar dispositivo"}


@router.post("/devices/{dev_addr}/equipment")
async def update_equipment(dev_addr: str, payload: dict = Body(...)):
    try:
        conn = _get_db()
        updates, params = ["updated_at = CURRENT_TIMESTAMP", "last_seen = CURRENT_TIMESTAMP"], []
        for k in ["name", "lat", "lon", "wifi_ssid", "wifi_rssi", "battery_pct", "temperature", "humidity", "device_type", "refresh_freq_s", "hw_version"]:
            if k in payload and payload[k] is not None:
                updates.append(f"{k} = ?")
                params.append(payload[k])
        conn.execute("INSERT OR IGNORE INTO devices (dev_addr) VALUES (?)", (dev_addr,))
        conn.execute(f"UPDATE devices SET {', '.join(updates)} WHERE dev_addr = ?", params + [dev_addr])
        conn.commit()
        row = conn.execute("SELECT name, device_type, refresh_freq_s FROM devices WHERE dev_addr = ?", (dev_addr,)).fetchone()
        conn.close()
        return {"ok": True, "config": {"name": row["name"] if row else None, "device_type": row["device_type"] if row else "sensor", "refresh_freq_s": row["refresh_freq_s"] if row else 60}}
    except Exception:
        return {"ok": False, "msg": "Error al actualizar equipo"}


@router.get("/devices/{dev_addr}/config")
async def get_device_config(dev_addr: str):
    try:
        conn = _get_db()
        row = conn.execute("SELECT name, device_type, refresh_freq_s FROM devices WHERE dev_addr = ?", (dev_addr,)).fetchone()
        conn.close()
        if row:
            return {"ok": True, "config": {"name": row["name"], "device_type": row["device_type"], "refresh_freq_s": row["refresh_freq_s"]}}
        return {"ok": True, "config": {"name": None, "device_type": "sensor", "refresh_freq_s": 60}}
    except Exception:
        return {"ok": True, "config": {"name": None, "device_type": "sensor", "refresh_freq_s": 60}}


# ── Config ─────────────────────────────────────────────────────────

@router.get("/config")
async def get_config():
    try:
        conn = _get_db()
        rows = conn.execute("SELECT key, value FROM config").fetchall()
        conn.close()
        return {r["key"]: r["value"] for r in rows}
    except Exception:
        return {}


@router.put("/config")
async def update_config(payload: dict = Body(...)):
    allowed = {"listen_port", "auth_password", "max_packets"}
    try:
        conn = _get_db()
        for k, v in payload.items():
            if k not in allowed:
                continue
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (k, str(v)))
        conn.commit()
        conn.close()
        return {"ok": True}
    except Exception:
        return {"ok": False, "msg": "Error al guardar config"}


# ── Clear ──────────────────────────────────────────────────────────

@router.post("/clear")
async def clear_data():
    try:
        conn = _get_db()
        conn.execute("DELETE FROM packets")
        conn.execute("DELETE FROM gateways")
        conn.execute("DELETE FROM devices")
        conn.commit()
        conn.close()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


# ── Real-time Stream (SSE) ─────────────────────────────────────────

@router.get("/stream")
async def stream_packets():
    import json as _json

    def _query_new(last_id: int | None) -> tuple[int | None, list[dict]]:
        conn = _get_db()
        try:
            if last_id is None:
                row = conn.execute("SELECT MAX(id) as mx FROM packets").fetchone()
                return (row["mx"] or 0), []
            rows = conn.execute(
                "SELECT p.*, g.name AS gateway_name, d.name AS device_name "
                "FROM packets p "
                "LEFT JOIN gateways g ON p.gateway_id = g.gateway_id "
                "LEFT JOIN devices d ON p.dev_addr = d.dev_addr "
                "WHERE p.id > ? ORDER BY p.id ASC", (last_id,)
            ).fetchall()
            return None, [dict(r) for r in rows]
        finally:
            conn.close()

    async def event_generator():
        last_id = None
        import time as _time
        last_ping = _time.time()
        while True:
            try:
                new_last, rows = await asyncio.to_thread(_query_new, last_id)
                if new_last is not None:
                    last_id = new_last
                for data in rows:
                    last_id = data["id"]
                    yield f"data: {_json.dumps(data, default=str)}\n\n"
                    last_ping = _time.time()
                # Comentario keep-alive para que nginx/proxy no maten la conexion
                if _time.time() - last_ping > 15:
                    yield ": keepalive\n\n"
                    last_ping = _time.time()
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/zone-events")
async def get_zone_events(limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        sql_text("""
            SELECT id, tenant_id, dev_addr, field_id, field_name, paddock_id, paddock_name,
                   lat, lon, event_type, created_at
            FROM device_zone_events
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {"limit": limit},
    )
    return {"events": [dict(r._mapping) for r in result.fetchall()]}
