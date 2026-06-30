import asyncio
import uuid
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
from fastapi import APIRouter, Query, Body, Depends, Request
from fastapi.responses import StreamingResponse
from app.core.config import settings
from app.core.deps import get_current_active_user, require_admin
from app.models.user import User

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

            CREATE TABLE IF NOT EXISTS pairing_attempts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                kind            TEXT NOT NULL,           -- 'gateway' | 'device'
                target_id       TEXT NOT NULL,           -- gateway_id o dev_addr
                code_attempted  TEXT,                    -- el código que mandó el usuario (hash-able para auditoría)
                result          TEXT NOT NULL,           -- 'ok' | 'not_found' | 'expired' | 'already_paired' | 'mismatch' | 'throttled' | 'error'
                reason          TEXT,                    -- mensaje legible
                ip              TEXT,
                user_agent      TEXT,
                user_id         TEXT,                    -- del JWT (si vino autenticado)
                created_at      TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            );
            CREATE INDEX IF NOT EXISTS idx_pairing_attempts_target ON pairing_attempts(target_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_pairing_attempts_result ON pairing_attempts(result, created_at);

            -- Snapshots previos a wipes destructivos, para poder restaurar.
            -- Se guardan como JSON (lista de filas) para que el schema pueda evolucionar.
            CREATE TABLE IF NOT EXISTS clear_snapshots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                kind        TEXT NOT NULL,           -- 'gateways' | 'devices' | 'all'
                payload     TEXT NOT NULL,           -- JSON con las filas completas
                reason      TEXT,                    -- ej: 'admin /lora/reset', 'auto pre-clear'
                user_id     TEXT,
                created_at  TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                restored_at TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_clear_snapshots_created ON clear_snapshots(created_at);
        """)

        # Migraciones defensivas para tablas pre-existentes
        for tbl, cols in [
            ("gateways", [
                ("is_paired",          "INTEGER DEFAULT 0"),
                ("pairing_code",       "TEXT"),
                ("pairing_expires_at", "TIMESTAMP"),
                ("last_paired_code",   "TEXT"),  # guarda el último código usado al pair, para reconocer reintentos
                ("wifi_ip",            "TEXT"),
                ("charging",           "INTEGER DEFAULT 0"),
                ("temperature",        "REAL"),
                ("humidity",           "REAL"),
                ("mac_aliases",        "TEXT"),  # IDs MAC (separados por coma) que se consolidan en esta fila paired
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
                ("last_paired_code",    "TEXT"),
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


# ── Pairing helpers (audit log + rate-limit) ────────────────────

# ── Pairing helpers (audit log + rate-limit) ────────────────────

async def _optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Devuelve el User si el request trae JWT válido; None si no hay token.

    Se usa en endpoints de pairing para que el audit log pueda registrar
    quién intentó (si estaba autenticado), sin obligar a estar logueado.
    """
    from app.core.security import decode_token
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        uid = uuid.UUID(sub)
    except (ValueError, TypeError):
        return None
    user = await db.get(User, uid)
    if user and user.is_active:
        return user
    return None


def _log_pair_attempt(
    conn: sqlite3.Connection,
    *,
    kind: str,             # 'gateway' | 'device'
    target_id: str,
    code_attempted: str | None,
    result: str,           # 'ok' | 'not_found' | 'expired' | 'already_paired' | 'mismatch' | 'throttled' | 'error'
    reason: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    user_id: str | None = None,
) -> None:
    """Registra un intento de pairing (ok o falla) para auditoría.

    Se hace best-effort: un fallo en la auditoría NO debe tumbar el endpoint
    de pairing. El caller debe encargarse de commitear la conexión.
    """
    try:
        conn.execute(
            """
            INSERT INTO pairing_attempts
                (kind, target_id, code_attempted, result, reason, ip, user_agent, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (kind, target_id, code_attempted, result, reason, ip, user_agent, user_id),
        )
    except Exception as e:
        print(f"[PAIR-AUDIT] no se pudo registrar intento: {e}")


def _pairing_throttled(conn: sqlite3.Connection, *, kind: str, target_id: str, ip: str | None) -> bool:
    """Devuelve True si se superó el límite de intentos en la ventana."""
    max_attempts = settings.PAIRING_MAX_ATTEMPTS
    window_s = settings.PAIRING_RATE_WINDOW_S
    if max_attempts <= 0 or window_s <= 0:
        return False
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) FROM pairing_attempts
            WHERE kind = ? AND target_id = ?
              AND created_at >= datetime('now', 'localtime', ?)
              AND result != 'ok'
            """,
            (kind, target_id, f"-{int(window_s)} seconds"),
        ).fetchone()
        fails = row[0] if row else 0
        if ip:
            row_ip = conn.execute(
                """
                SELECT COUNT(*) FROM pairing_attempts
                WHERE ip = ? AND created_at >= datetime('now', 'localtime', ?)
                  AND result != 'ok'
                """,
                (ip, f"-{int(window_s)} seconds"),
            ).fetchone()
            fails += row_ip[0] if row_ip else 0
        return fails >= max_attempts
    except Exception:
        return False


# ── Ingest (recibe paquetes del GW) ─────────────────────────────

@router.post("/ingest")
async def ingest(payload: dict = Body(...)):
    gw_id = payload.get("gateway_id", "?")
    payload_hex = payload.get("payload_hex", "")
    payload_json = payload.get("payload_json")

    conn = _get_db()
    try:
        # Alias lookup: si el gw_id es una MAC consolidada en una fila
        # paired, redirigir al gateway_id canónico antes de cualquier
        # INSERT OR IGNORE (que de otro modo recrea la fila de la MAC).
        if gw_id != "?":
            alias_row = conn.execute(
                "SELECT gateway_id FROM gateways "
                "WHERE is_paired = 1 AND (',' || COALESCE(mac_aliases, '') || ',') LIKE ?",
                (f"%,{gw_id},%",),
            ).fetchone()
            if alias_row:
                gw_id = alias_row["gateway_id"]
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

        # Si LORA_REQUIRE_PAIRING está activo, descartamos las lecturas
        # de devices no pareados (excepto "gw:" que son lecturas del propio
        # gateway). El device se auto-registra igual para que aparezca en
        # /devices/pending y el NOC/admin lo pueda emparejar.
        is_gateway_self_packet = bool(dev_addr) and dev_addr.startswith("gw:")
        is_first_seen = False
        device_is_paired = True  # default para no filtrar (gw: o dev_addr vacío)

        if dev_addr and not is_gateway_self_packet:
            row = conn.execute(
                "SELECT is_paired FROM devices WHERE dev_addr = ?", (dev_addr,),
            ).fetchone()
            if row is None:
                is_first_seen = True
                device_is_paired = False
            else:
                device_is_paired = bool(row["is_paired"])

        drop_packet = (
            settings.LORA_REQUIRE_PAIRING
            and dev_addr
            and not is_gateway_self_packet
            and not device_is_paired
            and not is_first_seen  # la primera lectura se guarda para que haya datos al parear
        )
        # Si es first-seen y require_pairing está activo, descartamos el packet
        # (sólo queremos que aparezca en /devices/pending; los datos reales se
        # empiezan a guardar recién cuando el device está paired).
        if is_first_seen and settings.LORA_REQUIRE_PAIRING:
            drop_packet = True

        if not drop_packet:
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
                    updates.append(
                        f"pairing_expires_at = datetime('now', '+{int(settings.PAIRING_TTL_MIN)} minutes')"
                    )
            conn.execute(
                f"UPDATE devices SET {', '.join(updates)} WHERE dev_addr = ?",
                params + [dev_addr],
            )

        conn.commit()
        status = "stored" if not drop_packet else "dropped-unpaired"
        print(f"[INGEST] GW={gw_id} Dev={dev_addr} {status} bat={battery}% temp={temperature}")
        return {
            "ok": True,
            "stored": not drop_packet,
            "reason": None if not drop_packet else "device_not_paired",
            "dev_addr": dev_addr,
        }
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
              AND g.pairing_expires_at > datetime('now')
            ORDER BY g.pairing_expires_at ASC
        """).fetchall()
        conn.close()
        return {"gateways": [dict(r) for r in rows]}
    except Exception:
        return {"gateways": []}


@router.post("/gateways/pair")
async def pair_gateway(
    payload: dict = Body(...),
    request: Request = None,  # type: ignore[assignment]
    current_user: User | None = Depends(_optional_user),
):
    """Empareja un gateway LoRa a partir de su código de pairing en pantalla.

    Devuelve códigos de error distintos en `code` para que el front pueda
    mostrar mensajes específicos:
      - 'invalid'     código vacío o no encontrado
      - 'expired'     el código existe pero está fuera de ventana
      - 'mismatch'    el código existe pero pertenece a otro gateway
      - 'already_paired' el GW ya está registrado
      - 'throttled'   demasiados intentos fallidos recientes
      - 'error'       error inesperado

    Todos los intentos (ok o falla) quedan registrados en `pairing_attempts`.
    """
    try:
        code = (payload.get("pairing_code") or "").strip()
        name = (payload.get("name") or "").strip()
        hint_gw_id = (payload.get("gateway_id") or "").strip() or None

        ip = None
        ua = None
        if request is not None:
            ip = request.client.host if request.client else None
            ua = request.headers.get("user-agent")
        user_id = str(current_user.id) if current_user else None

        conn = _get_db()

        if not code:
            _log_pair_attempt(
                conn,
                kind="gateway", target_id=hint_gw_id or "?",
                code_attempted=None, result="not_found",
                reason="pairing_code requerido",
                ip=ip, user_agent=ua, user_id=user_id,
            )
            conn.commit(); conn.close()
            return {"ok": False, "code": "invalid", "msg": "pairing_code requerido"}

        target_for_log = hint_gw_id or code

        if _pairing_throttled(conn, kind="gateway", target_id=target_for_log, ip=ip):
            _log_pair_attempt(
                conn, kind="gateway", target_id=target_for_log,
                code_attempted=code, result="throttled",
                reason="rate limit", ip=ip, user_agent=ua, user_id=user_id,
            )
            conn.commit(); conn.close()
            return {"ok": False, "code": "throttled",
                    "msg": "Demasiados intentos. Esperá unos minutos y volvé a intentar."}

        # Buscar por código primero (más confiable — el GW regenera códigos).
# Sólo códigos vigentes: si está expirado, lo manejamos abajo con un mensaje
# específico ("expired" en vez de "invalid") para que el front lo distinga.
        row = conn.execute(
            "SELECT gateway_id, pairing_code, pairing_expires_at, is_paired, name "
            "FROM gateways WHERE pairing_code = ? AND COALESCE(is_paired, 0) = 0 "
            "AND pairing_expires_at IS NOT NULL "
            "AND pairing_expires_at > datetime('now') "
            "ORDER BY pairing_expires_at DESC LIMIT 1",
            (code,),
        ).fetchone()

        # El código existe pero ya venció → marcamos expired
        if not row:
            expired_row = conn.execute(
                "SELECT gateway_id FROM gateways WHERE pairing_code = ? "
                "AND COALESCE(is_paired, 0) = 0 "
                "AND pairing_expires_at IS NOT NULL "
                "AND pairing_expires_at <= datetime('now') LIMIT 1",
                (code,),
            ).fetchone()
            if expired_row:
                _log_pair_attempt(
                    conn, kind="gateway", target_id=expired_row["gateway_id"],
                    code_attempted=code, result="expired",
                    reason="código fuera de ventana",
                    ip=ip, user_agent=ua, user_id=user_id,
                )
                conn.commit(); conn.close()
                return {"ok": False, "code": "expired",
                        "msg": "El código está caducado. Pedile al gateway que renueve (botón pairing) o usá el endpoint de refresh."}
            # El código no existe para ningún GW pending → puede que el GW ya esté paired.
            # Buscamos tanto en pairing_code activo como en last_paired_code histórico
            # (porque al hacer pair exitoso se borra pairing_code pero queda en last_paired_code).
            already_paired_row = conn.execute(
                "SELECT gateway_id FROM gateways WHERE "
                "(pairing_code = ? OR last_paired_code = ?) "
                "AND is_paired = 1 LIMIT 1",
                (code, code),
            ).fetchone()
            if already_paired_row:
                _log_pair_attempt(
                    conn, kind="gateway", target_id=already_paired_row["gateway_id"],
                    code_attempted=code, result="already_paired",
                    reason="código de GW ya registrado",
                    ip=ip, user_agent=ua, user_id=user_id,
                )
                conn.commit(); conn.close()
                return {"ok": False, "code": "already_paired",
                        "msg": "Este gateway ya está registrado."}
            _log_pair_attempt(
                conn, kind="gateway", target_id=target_for_log,
                code_attempted=code, result="not_found",
                reason="código no existe",
                ip=ip, user_agent=ua, user_id=user_id,
            )
            conn.commit()
            # Diagnóstico: si hay GWs pending, devolver los códigos
            # enmascarados (4****2) para que el user detecte typos.
            pending = [
                {
                    "gateway_id": r["gateway_id"],
                    "hint": (r["pairing_code"][:2] + "****"
                             + r["pairing_code"][-1:] if r["pairing_code"]
                             and len(r["pairing_code"]) >= 4 else "?"),
                    "expires_at": r["pairing_expires_at"],
                    "last_seen": r["last_seen"],
                }
                for r in conn.execute(
                    "SELECT gateway_id, pairing_code, pairing_expires_at, last_seen "
                    "FROM gateways WHERE COALESCE(is_paired, 0) = 0 "
                    "AND pairing_code IS NOT NULL "
                    "AND pairing_expires_at > datetime('now') "
                    "ORDER BY pairing_expires_at DESC"
                ).fetchall()
            ]
            conn.close()
            return {
                "ok": False,
                "code": "invalid",
                "msg": "Código de pairing inválido. Verificá que el gateway esté conectado y mostrando el código.",
                "pending_gateways": pending,
            }

        # Si no encontró por código pero el usuario dio un gateway_id,
        # verificar si ese GW tiene el código (podría haber regenerado)
        if not row and hint_gw_id:
            row = conn.execute(
                "SELECT gateway_id, pairing_code, pairing_expires_at, is_paired, name "
                "FROM gateways WHERE gateway_id = ?",
                (hint_gw_id,),
            ).fetchone()
            if row and (row["pairing_code"] or "") != code:
                _log_pair_attempt(
                    conn, kind="gateway", target_id=hint_gw_id,
                    code_attempted=code, result="mismatch",
                    reason="código no corresponde al gateway",
                    ip=ip, user_agent=ua, user_id=user_id,
                )
                conn.commit(); conn.close()
                return {"ok": False, "code": "mismatch",
                        "msg": "El código no corresponde a este gateway. Verifica el código en la pantalla OLED."}

        if row["is_paired"]:
            _log_pair_attempt(
                conn, kind="gateway", target_id=row["gateway_id"],
                code_attempted=code, result="already_paired",
                reason="gateway ya registrado",
                ip=ip, user_agent=ua, user_id=user_id,
            )
            conn.commit(); conn.close()
            return {"ok": False, "code": "already_paired",
                    "msg": "El gateway ya está registrado."}

        gw_id = row["gateway_id"]
        final_name = name if name else gw_id   # auto-asignar ID si no hay nombre

        conn.execute(
            """
            UPDATE gateways
               SET is_paired = 1,
                   name = ?,
                   pairing_code = NULL,
                   pairing_expires_at = NULL,
                   last_paired_code = ?,
                   updated_at = CURRENT_TIMESTAMP,
                   last_seen = CURRENT_TIMESTAMP
             WHERE gateway_id = ?
            """,
            (final_name, code, gw_id),
        )
        _log_pair_attempt(
            conn, kind="gateway", target_id=gw_id,
            code_attempted=code, result="ok",
            reason=f"paired as '{final_name}'",
            ip=ip, user_agent=ua, user_id=user_id,
        )
        conn.commit()
        conn.close()
        return {"ok": True, "code": "ok", "gateway_id": gw_id, "name": final_name}
    except Exception as e:
        try:
            conn = _get_db()
            _log_pair_attempt(
                conn, kind="gateway", target_id="?",
                code_attempted=(payload or {}).get("pairing_code"),
                result="error", reason=str(e),
            )
            conn.commit(); conn.close()
        except Exception:
            pass
        return {"ok": False, "code": "error", "msg": f"Error al emparejar: {e}"}


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
async def delete_gateway(
    gateway_id: str,
    request: Request,
    force: bool = Query(False, description="Borra aunque esté paired y limpia packets asociados"),
    current_user: User = Depends(require_admin),
):
    """Elimina un gateway. Sólo admin.

    Sin `force=true`: falla con `is_paired` si está registrado.
    Con `force=true`: revierte is_paired, borra los packets asociados y
    registra la acción en el audit log.
    """
    try:
        conn = _get_db()
        row = conn.execute(
            "SELECT is_paired FROM gateways WHERE gateway_id = ?", (gateway_id,),
        ).fetchone()
        if not row:
            conn.close()
            return {"ok": False, "code": "not_found", "msg": "Gateway no existe"}
        if row["is_paired"] and not force:
            conn.close()
            return {
                "ok": False,
                "code": "is_paired",
                "msg": ("El gateway está registrado (is_paired=1). Para eliminarlo "
                        "de todas formas, mandá ?force=true (admin) — eso borra "
                        "también los packets asociados."),
            }

        packets_deleted = 0
        # Siempre limpiamos los packets asociados (así no quedan huérfanos
        # en queries de /packets que filtren por gateway_id).
        cur = conn.execute("DELETE FROM packets WHERE gateway_id = ?", (gateway_id,))
        packets_deleted = cur.rowcount
        if force:
            _log_pair_attempt(
                conn, kind="gateway", target_id=gateway_id,
                code_attempted=None, result="ok",
                reason=(f"force-delete by {current_user.email} "
                        f"(was_paired, packets_deleted={packets_deleted})"),
                ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                user_id=str(current_user.id),
            )
        conn.execute("DELETE FROM gateways WHERE gateway_id=?", (gateway_id,))
        conn.commit()
        conn.close()
        return {"ok": True, "packets_deleted": packets_deleted}
    except Exception:
        return {"ok": False, "msg": "Error al eliminar gateway"}


@router.post("/gateway/sync")
async def sync_gateway(payload: dict = Body(...), db: AsyncSession = Depends(get_db)):
    try:
        gw_id = payload.get("gateway_id")
        if not gw_id:
            return {"ok": False, "msg": "gateway_id requerido"}

        conn = _get_db()

        # ── Alias lookup ─────────────────────────────────────────────────
        # Si este gw_id (típicamente la MAC del ESP32) fue consolidado antes
        # con una fila paired via mac_aliases, redirigir todo el flujo a esa
        # fila canónica. Esto evita que cada sync recree la fila de la MAC.
        alias_row = conn.execute(
            "SELECT gateway_id FROM gateways "
            "WHERE is_paired = 1 AND (',' || COALESCE(mac_aliases, '') || ',') LIKE ?",
            (f"%,{gw_id},%",),
        ).fetchone()
        if alias_row:
            gw_id = alias_row["gateway_id"]

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
            "SELECT is_paired, pairing_code FROM gateways WHERE gateway_id = ?", (gw_id,)
        ).fetchone()
        is_already_paired = existing_paired and existing_paired["is_paired"]

        # Si el GW trae pairing_code y aún no está paired → guardarlo
        if payload.get("pairing_code") and not is_already_paired:
            updates.append("pairing_code = ?")
            params.append(payload["pairing_code"])
            # El server SIEMPRE estampa la expiración (no confiar en el reloj
            # del GW, puede estar sin NTP). Si el GW manda su propio expiry,
            # se ignora para evitar pares con códigos que ya vencieron en server.
            updates.append(
                f"pairing_expires_at = datetime('now', '+{int(settings.PAIRING_TTL_MIN)} minutes')"
            )
        # Si el GW ya tenía un código pending y la auto-renovación está activa,
        # extender la ventana para que el usuario tenga tiempo de tipearlo.
        elif (
            settings.PAIRING_AUTO_RENEW
            and not is_already_paired
            and existing_paired
            and existing_paired["pairing_code"]
        ):
            updates.append(
                f"pairing_expires_at = datetime('now', '+{int(settings.PAIRING_TTL_MIN)} minutes')"
            )

        conn.execute(f"UPDATE gateways SET {', '.join(updates)} WHERE gateway_id = ?", params + [gw_id])

        # ── Alias merge ──────────────────────────────────────────────────
        # Si el GW envía un nombre que coincide con una fila paired existente
        # (típico: GW nuevo con MAC `E85C...` que se debe consolidar con la
        # entrada `GW-EXA` registrada por el usuario), adopta la fila paired
        # como canónica: migra packets/devices, borra la fila auto-registrada
        # y deja el sync trabajando contra el gateway_id amigable.
        sync_name = (payload.get("name") or "").strip()
        if sync_name and not is_already_paired:
            canon = conn.execute(
                "SELECT gateway_id, mac_aliases FROM gateways "
                "WHERE is_paired = 1 AND lower(name) = lower(?) AND gateway_id != ?",
                (sync_name, gw_id),
            ).fetchone()
            if canon:
                canon_id = canon["gateway_id"]
                # 1. Aplicar los mismos campos del sync sobre la fila canónica
                conn.execute(
                    f"UPDATE gateways SET {', '.join(updates)} WHERE gateway_id = ?",
                    params + [canon_id],
                )
                # 2. Migrar FKs lógicas (packets, devices) del MAC → canónico
                conn.execute(
                    "UPDATE packets SET gateway_id = ? WHERE gateway_id = ?",
                    (canon_id, gw_id),
                )
                conn.execute(
                    "UPDATE devices SET gateway_id = ? WHERE gateway_id = ?",
                    (canon_id, gw_id),
                )
                # 3. Persistir el MAC como alias para que próximos syncs
                #    se redirijan directo sin pasar por este merge.
                existing_aliases = canon["mac_aliases"] or ""
                alias_list = [a.strip() for a in existing_aliases.split(",") if a.strip()]
                if gw_id not in alias_list:
                    alias_list.append(gw_id)
                    conn.execute(
                        "UPDATE gateways SET mac_aliases = ? WHERE gateway_id = ?",
                        (",".join(alias_list), canon_id),
                    )
                # 4. Borrar la fila auto-registrada
                conn.execute("DELETE FROM gateways WHERE gateway_id = ?", (gw_id,))
                gw_id = canon_id

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
    """Lista devices pendientes de parear.

    Incluye tanto los que tienen pairing_code vigente como los que fueron
    auto-registrados por una lectura entrante (típicamente dev_addr='raw-XXXX')
    pero todavía no trajeron código de pairing. Esos últimos aparecen con
    `pairing_code=null` y `pairing_state='awaiting_code'`.
    """
    try:
        conn = _get_db()
        rows = conn.execute(
            """
            SELECT d.dev_addr, d.name, d.device_type, d.pairing_code,
                   d.pairing_expires_at, d.last_seen, d.battery_pct,
                   d.temperature, d.created_at, d.is_paired,
                   CASE
                       WHEN d.pairing_code IS NULL THEN 'awaiting_code'
                       WHEN d.pairing_expires_at IS NULL
                            OR d.pairing_expires_at <= datetime('now') THEN 'code_expired'
                       ELSE 'code_active'
                   END AS pairing_state,
                   (SELECT COUNT(*) FROM packets p
                    WHERE p.dev_addr = d.dev_addr
                      AND p.created_at >= datetime('now','localtime','-1 hour')) AS packets_last_hour,
                   (SELECT COUNT(*) FROM packets p
                    WHERE p.dev_addr = d.dev_addr) AS packets_total
            FROM devices d
            WHERE COALESCE(d.is_paired, 0) = 0
              AND d.dev_addr NOT LIKE 'gw:%'
            ORDER BY d.last_seen DESC
            """,
        ).fetchall()
        conn.close()
        return {"devices": [dict(r) for r in rows]}
    except Exception:
        return {"devices": []}


@router.post("/devices/pair")
async def pair_device(
    payload: dict = Body(...),
    request: Request = None,  # type: ignore[assignment]
    current_user: User | None = Depends(_optional_user),
):
    """Empareja un dispositivo LoRa seleccionándolo de la lista de pending.

    Devuelve códigos de error distintos:
      - 'invalid'          sin dev_addr o no encontrado
      - 'already_paired'   el device ya está registrado
      - 'throttled'        rate limit excedido
      - 'error'            error inesperado

    Todos los intentos quedan auditados en `pairing_attempts`.
    """
    try:
        dev_addr = (payload.get("dev_addr") or "").strip()
        name = (payload.get("name") or "").strip()

        ip = None
        ua = None
        if request is not None:
            ip = request.client.host if request.client else None
            ua = request.headers.get("user-agent")
        user_id = str(current_user.id) if current_user else None

        conn = _get_db()

        if not dev_addr:
            _log_pair_attempt(
                conn, kind="device", target_id="?",
                code_attempted=None, result="not_found",
                reason="dev_addr requerido",
                ip=ip, user_agent=ua, user_id=user_id,
            )
            conn.commit(); conn.close()
            return {"ok": False, "code": "invalid", "msg": "dev_addr requerido"}

        if _pairing_throttled(conn, kind="device", target_id=dev_addr, ip=ip):
            _log_pair_attempt(
                conn, kind="device", target_id=dev_addr,
                code_attempted=None, result="throttled",
                reason="rate limit", ip=ip, user_agent=ua, user_id=user_id,
            )
            conn.commit(); conn.close()
            return {"ok": False, "code": "throttled",
                    "msg": "Demasiados intentos. Esperá unos minutos."}

        row = conn.execute(
            "SELECT dev_addr, pairing_code, pairing_expires_at, is_paired, name "
            "FROM devices WHERE dev_addr = ?",
            (dev_addr,),
        ).fetchone()

        if not row:
            _log_pair_attempt(
                conn, kind="device", target_id=dev_addr,
                code_attempted=None, result="not_found",
                reason="device no existe",
                ip=ip, user_agent=ua, user_id=user_id,
            )
            conn.commit(); conn.close()
            return {"ok": False, "code": "invalid",
                    "msg": "Dispositivo no encontrado"}

        if row["is_paired"]:
            _log_pair_attempt(
                conn, kind="device", target_id=dev_addr,
                code_attempted=None, result="already_paired",
                reason="device ya registrado",
                ip=ip, user_agent=ua, user_id=user_id,
            )
            conn.commit(); conn.close()
            return {"ok": False, "code": "already_paired",
                    "msg": "El dispositivo ya está registrado"}

        final_name = name if name else (row["name"] or dev_addr)

        conn.execute(
            """
            UPDATE devices
               SET is_paired = 1,
                   name = ?,
                   pairing_code = NULL,
                   pairing_expires_at = NULL,
                   last_paired_code = COALESCE(pairing_code, last_paired_code),
                   updated_at = CURRENT_TIMESTAMP,
                   last_seen = CURRENT_TIMESTAMP
             WHERE dev_addr = ?
            """,
            (final_name, dev_addr),
        )
        _log_pair_attempt(
            conn, kind="device", target_id=dev_addr,
            code_attempted=None, result="ok",
            reason=f"paired as '{final_name}'",
            ip=ip, user_agent=ua, user_id=user_id,
        )
        conn.commit()
        conn.close()
        return {"ok": True, "code": "ok", "dev_addr": dev_addr, "name": final_name}
    except Exception as e:
        try:
            conn = _get_db()
            _log_pair_attempt(
                conn, kind="device", target_id=(payload or {}).get("dev_addr", "?"),
                code_attempted=None, result="error", reason=str(e),
            )
            conn.commit(); conn.close()
        except Exception:
            pass
        return {"ok": False, "code": "error", "msg": f"Error al emparejar: {e}"}


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


# ── Pairing admin: refresh / regenerate / audit log ───────────────

@router.post("/gateways/{gw_id}/pairing/refresh")
async def refresh_gateway_pairing(
    gw_id: str,
    request: Request,
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(require_admin),
):
    """Extiende la ventana del código actual sin tocarlo (útil mientras el
    usuario está tipeándolo en otra pestaña). Si no hay código, genera uno
    nuevo de 6 dígitos. Sólo admin.

    Body opcional: { "ttl_min": 30 } (override por-request).
    """
    ttl = int(payload.get("ttl_min") or settings.PAIRING_TTL_MIN)
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT gateway_id, pairing_code, is_paired FROM gateways WHERE gateway_id = ?",
            (gw_id,),
        ).fetchone()
        if not row:
            conn.close()
            return {"ok": False, "code": "not_found", "msg": "Gateway no encontrado"}

        if row["is_paired"]:
            conn.close()
            return {"ok": False, "code": "already_paired",
                    "msg": "El gateway ya está registrado"}

        new_code = row["pairing_code"] or _gen_random_code(6)
        conn.execute(
            """
            UPDATE gateways
               SET pairing_code = ?,
                   pairing_expires_at = datetime('now', ?)
             WHERE gateway_id = ?
            """,
            (new_code, f"+{ttl} minutes", gw_id),
        )
        _log_pair_attempt(
            conn, kind="gateway", target_id=gw_id,
            code_attempted=None, result="ok",
            reason=f"admin refresh ({current_user.email}) ttl={ttl}min",
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            user_id=str(current_user.id),
        )
        conn.commit()
        conn.close()
        return {"ok": True, "code": new_code, "expires_in_min": ttl,
                "gateway_id": gw_id}
    except Exception as e:
        conn.close()
        return {"ok": False, "code": "error", "msg": str(e)}


@router.post("/gateways/{gw_id}/pairing/regenerate")
async def regenerate_gateway_pairing(
    gw_id: str,
    request: Request,
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(require_admin),
):
    """Fuerza un código NUEVO (invalida el anterior) y estampa la expiración.
    Útil cuando el código actual ya está comprometido o expirado.
    """
    ttl = int(payload.get("ttl_min") or settings.PAIRING_TTL_MIN)
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT gateway_id, is_paired FROM gateways WHERE gateway_id = ?",
            (gw_id,),
        ).fetchone()
        if not row:
            conn.close()
            return {"ok": False, "code": "not_found", "msg": "Gateway no encontrado"}

        if row["is_paired"]:
            conn.close()
            return {"ok": False, "code": "already_paired",
                    "msg": "El gateway ya está registrado"}

        new_code = _gen_random_code(6)
        conn.execute(
            """
            UPDATE gateways
               SET pairing_code = ?,
                   pairing_expires_at = datetime('now', ?)
             WHERE gateway_id = ?
            """,
            (new_code, f"+{ttl} minutes", gw_id),
        )
        _log_pair_attempt(
            conn, kind="gateway", target_id=gw_id,
            code_attempted=None, result="ok",
            reason=f"admin regenerate ({current_user.email}) ttl={ttl}min",
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            user_id=str(current_user.id),
        )
        conn.commit()
        conn.close()
        return {"ok": True, "code": new_code, "expires_in_min": ttl,
                "gateway_id": gw_id}
    except Exception as e:
        conn.close()
        return {"ok": False, "code": "error", "msg": str(e)}


@router.post("/gateways/{gw_id}/pairing/accept-code")
async def accept_pairing_code(
    gw_id: str,
    request: Request,
    payload: dict = Body(...),
    current_user: User = Depends(require_admin),
):
    """Le dice al server: "estoy mirando el GW y muestra este código".

    Caso de uso: el ESP32 reseteó y generó un código nuevo, pero todavía
    no hizo su primer sync post-reset → la DB tiene un código distinto
    al que muestra la pantalla. El admin (que está físicamente con el GW)
    llama a este endpoint con el código que ve, y a partir de ahí el
    endpoint /gateways/pair acepta ese código.

    Si después el GW sincroniza con un código distinto, el comportamiento
    normal de /gateway/sync sobreescribirá — pero我们已经解决了 la ventana.

    Body: { "code": "123456" }
    """
    code = (payload.get("code") or "").strip()
    if not code or not code.isdigit() or not (4 <= len(code) <= 8):
        return {"ok": False, "code": "invalid",
                "msg": "code requerido (4-8 dígitos numéricos)"}
    ttl = int(payload.get("ttl_min") or settings.PAIRING_TTL_MIN)
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT gateway_id, is_paired, pairing_code, pairing_expires_at "
            "FROM gateways WHERE gateway_id = ?",
            (gw_id,),
        ).fetchone()
        if not row:
            conn.close()
            return {"ok": False, "code": "not_found", "msg": "Gateway no encontrado"}
        if row["is_paired"]:
            conn.close()
            return {"ok": False, "code": "already_paired",
                    "msg": "El gateway ya está registrado"}

        previous = row["pairing_code"]
        conn.execute(
            """
            UPDATE gateways
               SET pairing_code = ?,
                   pairing_expires_at = datetime('now', ?)
             WHERE gateway_id = ?
            """,
            (code, f"+{ttl} minutes", gw_id),
        )
        _log_pair_attempt(
            conn, kind="gateway", target_id=gw_id,
            code_attempted=code, result="ok",
            reason=(f"admin accept-code ({current_user.email}) "
                    f"prev={previous} ttl={ttl}min"),
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            user_id=str(current_user.id),
        )
        conn.commit()
        conn.close()
        return {
            "ok": True,
            "code": code,
            "previous_code": previous,
            "expires_in_min": ttl,
            "gateway_id": gw_id,
        }
    except Exception as e:
        conn.close()
        return {"ok": False, "code": "error", "msg": str(e)}


@router.post("/gateways/{gw_id}/aliases")
async def add_gateway_alias(
    gw_id: str,
    payload: dict = Body(...),
    current_user: User = Depends(require_admin),
):
    """Vincula un gateway_id (típicamente la MAC del ESP32) como alias de la
    fila paired `gw_id`. A partir de acá, cada /gateway/sync que llegue con
    ese MAC se redirige a esta fila y no se crea una nueva.

    Body: { "mac": "E85C65BA2010" }
    """
    mac = (payload.get("mac") or "").strip()
    if not mac:
        return {"ok": False, "msg": "mac requerido"}
    if mac == gw_id:
        return {"ok": False, "msg": "mac debe ser distinto de gateway_id"}

    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT gateway_id, is_paired, mac_aliases FROM gateways WHERE gateway_id = ?",
            (gw_id,),
        ).fetchone()
        if not row:
            return {"ok": False, "msg": f"gateway {gw_id} no existe"}
        if not row["is_paired"]:
            return {"ok": False, "msg": f"gateway {gw_id} no está paired"}

        # Migrar FKs lógicas del MAC hacia la fila canónica (idempotente)
        conn.execute(
            "UPDATE packets SET gateway_id = ? WHERE gateway_id = ?",
            (gw_id, mac),
        )
        conn.execute(
            "UPDATE devices SET gateway_id = ? WHERE gateway_id = ?",
            (gw_id, mac),
        )
        # Borrar fila auto-registrada si existe
        conn.execute("DELETE FROM gateways WHERE gateway_id = ?", (mac,))

        existing = row["mac_aliases"] or ""
        aliases = [a.strip() for a in existing.split(",") if a.strip()]
        if mac not in aliases:
            aliases.append(mac)
        conn.execute(
            "UPDATE gateways SET mac_aliases = ? WHERE gateway_id = ?",
            (",".join(aliases), gw_id),
        )
        conn.commit()
        return {"ok": True, "gateway_id": gw_id, "mac_aliases": aliases}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "msg": str(e)}
    finally:
        conn.close()


@router.get("/pairing/attempts")
async def list_pairing_attempts(
    kind: str | None = Query(None, pattern="^(gateway|device)$"),
    target_id: str | None = Query(None),
    result: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_admin),
):
    """Audit log de intentos de pairing (últimos N). Sólo admin."""
    conn = _get_db()
    try:
        where = []
        params = []
        if kind:
            where.append("kind = ?"); params.append(kind)
        if target_id:
            where.append("target_id = ?"); params.append(target_id)
        if result:
            where.append("result = ?"); params.append(result)
        sql = "SELECT id, kind, target_id, code_attempted, result, reason, ip, user_agent, user_id, created_at FROM pairing_attempts"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return {"attempts": [dict(r) for r in rows]}
    except Exception as e:
        conn.close()
        return {"attempts": [], "msg": str(e)}


def _gen_random_code(n: int = 6) -> str:
    """Genera un código numérico de N dígitos (equivalente al del ESP32)."""
    import secrets
    return f"{secrets.randbelow(10 ** n):0{n}d}"


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
async def delete_device(
    dev_addr: str,
    request: Request,
    force: bool = Query(False, description="Borra aunque esté paired y limpia packets asociados"),
    current_user: User = Depends(require_admin),
):
    """Elimina un device. Sólo admin.

    Sin `force=true`: falla con `is_paired` si está registrado.
    Con `force=true`: revierte is_paired, borra los packets asociados y
    registra la acción en el audit log.
    """
    try:
        conn = _get_db()
        row = conn.execute(
            "SELECT is_paired FROM devices WHERE dev_addr = ?", (dev_addr,),
        ).fetchone()
        if not row:
            conn.close()
            return {"ok": False, "code": "not_found", "msg": "Device no existe"}
        if row["is_paired"] and not force:
            conn.close()
            return {
                "ok": False,
                "code": "is_paired",
                "msg": ("El device está registrado (is_paired=1). Para eliminarlo "
                        "de todas formas, mandá ?force=true (admin) — eso borra "
                        "también los packets asociados."),
            }

        packets_deleted = 0
        # Siempre limpiamos los packets asociados (evitamos huérfanos).
        cur = conn.execute("DELETE FROM packets WHERE dev_addr = ?", (dev_addr,))
        packets_deleted = cur.rowcount
        if force:
            _log_pair_attempt(
                conn, kind="device", target_id=dev_addr,
                code_attempted=None, result="ok",
                reason=(f"force-delete by {current_user.email} "
                        f"(was_paired, packets_deleted={packets_deleted})"),
                ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                user_id=str(current_user.id),
            )
        conn.execute("DELETE FROM devices WHERE dev_addr=?", (dev_addr,))
        conn.commit()
        conn.close()
        return {"ok": True, "packets_deleted": packets_deleted}
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


# ── Clear / Reset ─────────────────────────────────────────────────
#
# Los endpoints destructivos están separados para evitar perder estado de
# pairing. "clear" sólo borra packets; gateways y devices se limpian con
# endpoints dedicados que rechazan borrar filas paired. "reset" es la
# opción nuclear (wipe total) y exige confirm=true.

import json as _json


def _take_snapshot(conn: sqlite3.Connection, kind: str, reason: str, user_id: str | None) -> int:
    """Hace un JSON snapshot de las tablas a borrar y lo guarda.

    Devuelve el id del snapshot. Si no había filas, devuelve 0 y no guarda nada.
    """
    payloads: dict[str, list[dict]] = {}
    if kind in ("gateways", "all"):
        payloads["gateways"] = [dict(r) for r in conn.execute("SELECT * FROM gateways").fetchall()]
    if kind in ("devices", "all"):
        payloads["devices"] = [dict(r) for r in conn.execute("SELECT * FROM devices").fetchall()]
    if not any(payloads.values()):
        return 0
    cur = conn.execute(
        "INSERT INTO clear_snapshots (kind, payload, reason, user_id) VALUES (?, ?, ?, ?)",
        (kind, _json.dumps(payloads, default=str), reason, user_id),
    )
    return cur.lastrowid or 0


@router.post("/clear")
async def clear_packets(current_user: User = Depends(require_admin)):
    """Borra SOLO packets (lecturas). No toca gateways ni devices.

    Use los endpoints /lora/clear/gateways o /lora/clear/devices para limpiar
    inventario (siempre admin-only y rechazando filas paired).
    """
    try:
        conn = _get_db()
        cur = conn.execute("DELETE FROM packets")
        deleted = cur.rowcount
        conn.commit()
        conn.close()
        print(f"[CLEAR] packets deleted={deleted} by={current_user.email}")
        return {"ok": True, "deleted_packets": deleted}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


@router.post("/clear/gateways")
async def clear_gateways(current_user: User = Depends(require_admin)):
    """Borra gateways NO paired. Antes hace snapshot para poder restaurar.

    Falla si hay al menos un gateway paired (eso requiere /lora/reset).
    """
    try:
        conn = _get_db()
        paired = conn.execute(
            "SELECT COUNT(*) FROM gateways WHERE is_paired = 1"
        ).fetchone()[0]
        if paired:
            conn.close()
            return {
                "ok": False,
                "code": "has_paired",
                "msg": (f"Hay {paired} gateway(s) registrado(s). Usá /lora/reset "
                        "para wipe total, o desregistralos uno por uno."),
            }
        snap_id = _take_snapshot(conn, "gateways", "admin /lora/clear/gateways", str(current_user.id))
        cur = conn.execute("DELETE FROM gateways")
        deleted = cur.rowcount
        conn.commit()
        conn.close()
        return {
            "ok": True,
            "deleted_gateways": deleted,
            "snapshot_id": snap_id,
        }
    except Exception as e:
        return {"ok": False, "msg": str(e)}


@router.post("/clear/devices")
async def clear_devices(current_user: User = Depends(require_admin)):
    """Borra devices NO paired. Antes hace snapshot para poder restaurar.

    Falla si hay al menos un device paired.
    """
    try:
        conn = _get_db()
        paired = conn.execute(
            "SELECT COUNT(*) FROM devices WHERE is_paired = 1"
        ).fetchone()[0]
        if paired:
            conn.close()
            return {
                "ok": False,
                "code": "has_paired",
                "msg": (f"Hay {paired} device(s) registrado(s). Usá /lora/reset "
                        "para wipe total, o desregistralos uno por uno."),
            }
        snap_id = _take_snapshot(conn, "devices", "admin /lora/clear/devices", str(current_user.id))
        cur = conn.execute("DELETE FROM devices")
        deleted = cur.rowcount
        conn.commit()
        conn.close()
        return {
            "ok": True,
            "deleted_devices": deleted,
            "snapshot_id": snap_id,
        }
    except Exception as e:
        return {"ok": False, "msg": str(e)}


@router.post("/reset")
async def reset_lora_db(
    payload: dict = Body(default_factory=dict),
    current_user: User = Depends(require_admin),
):
    """WIPE TOTAL de la DB LoRa (packets + gateways + devices + pairing_attempts).

    Hace snapshot de todo antes de borrar para poder restaurar. Requiere
    body {"confirm": true} para evitar wipes accidentales.
    """
    if not payload.get("confirm"):
        return {
            "ok": False,
            "code": "confirm_required",
            "msg": ("Reset destructivo. Para confirmar, mandá body "
                    "{\"confirm\": true}. Podés restaurar con el snapshot_id "
                    "que devuelve la respuesta."),
        }
    try:
        conn = _get_db()
        snap_id = _take_snapshot(
            conn, "all", "admin /lora/reset", str(current_user.id),
        )
        cur_p = conn.execute("DELETE FROM packets")
        cur_g = conn.execute("DELETE FROM gateways")
        cur_d = conn.execute("DELETE FROM devices")
        cur_a = conn.execute("DELETE FROM pairing_attempts")
        conn.commit()
        conn.close()
        print(f"[RESET] full wipe by={current_user.email} "
              f"packets={cur_p.rowcount} gateways={cur_g.rowcount} "
              f"devices={cur_d.rowcount} attempts={cur_a.rowcount}")
        return {
            "ok": True,
            "deleted": {
                "packets": cur_p.rowcount,
                "gateways": cur_g.rowcount,
                "devices": cur_d.rowcount,
                "pairing_attempts": cur_a.rowcount,
            },
            "snapshot_id": snap_id,
        }
    except Exception as e:
        return {"ok": False, "msg": str(e)}


@router.get("/clear/snapshots")
async def list_snapshots(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_admin),
):
    """Lista snapshots previos a wipes. Sólo admin."""
    conn = _get_db()
    try:
        rows = conn.execute(
            """
            SELECT id, kind, reason, user_id, created_at, restored_at,
                   length(payload) AS payload_bytes
              FROM clear_snapshots
             ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        conn.close()
        return {"snapshots": [dict(r) for r in rows]}
    except Exception as e:
        conn.close()
        return {"snapshots": [], "msg": str(e)}


@router.post("/clear/snapshots/{snapshot_id}/restore")
async def restore_snapshot(
    snapshot_id: int,
    current_user: User = Depends(require_admin),
):
    """Restaura un snapshot (re-insert con INSERT OR IGNORE). No borra nada
    que ya exista — sólo completa lo que falta."""
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT * FROM clear_snapshots WHERE id = ?", (snapshot_id,),
        ).fetchone()
        if not row:
            conn.close()
            return {"ok": False, "code": "not_found", "msg": "Snapshot no existe"}
        if row["restored_at"]:
            conn.close()
            return {
                "ok": False,
                "code": "already_restored",
                "msg": f"Este snapshot ya fue restaurado el {row['restored_at']}",
            }

        payload = _json.loads(row["payload"])
        restored_gw = 0
        restored_dev = 0

        for gw in payload.get("gateways", []):
            cols = [k for k in gw.keys() if k != "id"]
            placeholders = ",".join(["?"] * len(cols))
            try:
                cur = conn.execute(
                    f"INSERT OR IGNORE INTO gateways ({','.join(cols)}) "
                    f"VALUES ({placeholders})",
                    [gw[c] for c in cols],
                )
                restored_gw += cur.rowcount
            except Exception as e:
                print(f"[RESTORE] gw {gw.get('gateway_id')}: {e}")

        for dev in payload.get("devices", []):
            cols = [k for k in dev.keys() if k != "id"]
            placeholders = ",".join(["?"] * len(cols))
            try:
                cur = conn.execute(
                    f"INSERT OR IGNORE INTO devices ({','.join(cols)}) "
                    f"VALUES ({placeholders})",
                    [dev[c] for c in cols],
                )
                restored_dev += cur.rowcount
            except Exception as e:
                print(f"[RESTORE] dev {dev.get('dev_addr')}: {e}")

        conn.execute(
            "UPDATE clear_snapshots SET restored_at = datetime('now','localtime') "
            "WHERE id = ?",
            (snapshot_id,),
        )
        conn.commit()
        conn.close()
        return {
            "ok": True,
            "restored_gateways": restored_gw,
            "restored_devices": restored_dev,
            "snapshot_id": snapshot_id,
        }
    except Exception as e:
        conn.close()
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
