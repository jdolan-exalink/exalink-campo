import os
import time
import json
import binascii
import sqlite3
from collections import deque
from threading import Lock

from flask import Flask, request, jsonify

LISTEN_PORT   = int(os.environ.get("LORA_LISTEN_PORT", 6666))
AUTH_PASSWORD = os.environ.get("LORA_AUTH_PASSWORD", "abc1234")
MAX_PACKETS   = int(os.environ.get("LORA_MAX_PACKETS", 500))
DB_PATH       = os.environ.get("LORA_DB_PATH", "DB/lora.db")

app = Flask(__name__)
lock = Lock()
packets = deque(maxlen=MAX_PACKETS)
started_at = time.time()


def _get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _get_db()
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
            mtype_str   TEXT,
            fcnt        INTEGER,
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
            humidity       REAL,
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
    existing_packet_columns = {row["name"] for row in conn.execute("PRAGMA table_info(packets)").fetchall()}
    if "temperature" not in existing_packet_columns:
        conn.execute("ALTER TABLE packets ADD COLUMN temperature REAL")
    if "humidity" not in existing_packet_columns:
        conn.execute("ALTER TABLE packets ADD COLUMN humidity REAL")
    if "battery" not in existing_packet_columns:
        conn.execute("ALTER TABLE packets ADD COLUMN battery REAL")
    if "charging" not in existing_packet_columns:
        conn.execute("ALTER TABLE packets ADD COLUMN charging INTEGER DEFAULT 0")
    if "wake_boots" not in existing_packet_columns:
        conn.execute("ALTER TABLE packets ADD COLUMN wake_boots INTEGER")
    if "wake_time_ms" not in existing_packet_columns:
        conn.execute("ALTER TABLE packets ADD COLUMN wake_time_ms INTEGER")
    existing_device_columns = {row["name"] for row in conn.execute("PRAGMA table_info(devices)").fetchall()}
    if "temperature" not in existing_device_columns:
        conn.execute("ALTER TABLE devices ADD COLUMN temperature REAL")
    if "humidity" not in existing_device_columns:
        conn.execute("ALTER TABLE devices ADD COLUMN humidity REAL")
    if "gps_fresh" not in existing_device_columns:
        conn.execute("ALTER TABLE devices ADD COLUMN gps_fresh INTEGER DEFAULT 0")
    existing_gw_columns = {row["name"] for row in conn.execute("PRAGMA table_info(gateways)").fetchall()}
    if "wifi_ip" not in existing_gw_columns:
        conn.execute("ALTER TABLE gateways ADD COLUMN wifi_ip TEXT")
    if "is_paired" not in existing_gw_columns:
        conn.execute("ALTER TABLE gateways ADD COLUMN is_paired INTEGER DEFAULT 0")
    if "pairing_code" not in existing_gw_columns:
        conn.execute("ALTER TABLE gateways ADD COLUMN pairing_code TEXT")
    if "pairing_expires_at" not in existing_gw_columns:
        conn.execute("ALTER TABLE gateways ADD COLUMN pairing_expires_at TIMESTAMP")
    existing_dev2_columns = {row["name"] for row in conn.execute("PRAGMA table_info(devices)").fetchall()}
    if "wifi_ip" not in existing_dev2_columns:
        conn.execute("ALTER TABLE devices ADD COLUMN wifi_ip TEXT")
    conn.commit()
    conn.close()


def _init_config():
    conn = _get_db()
    defaults = {
        "listen_port":   str(LISTEN_PORT),
        "auth_password": AUTH_PASSWORD,
        "max_packets":   str(MAX_PACKETS),
    }
    for k, v in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)", (k, v)
        )
    conn.commit()
    conn.close()


def _reload_config():
    global AUTH_PASSWORD, MAX_PACKETS, packets
    conn = _get_db()
    rows = conn.execute("SELECT key, value FROM config").fetchall()
    conn.close()
    cfg = {r["key"]: r["value"] for r in rows}
    AUTH_PASSWORD = cfg.get("auth_password", AUTH_PASSWORD)
    new_max = int(cfg.get("max_packets", MAX_PACKETS))
    if new_max != MAX_PACKETS:
        MAX_PACKETS = new_max
        packets = deque(packets, maxlen=MAX_PACKETS)


def _check_auth():
    auth = request.headers.get("Authorization", "")
    expected = f"Bearer {AUTH_PASSWORD}"
    if AUTH_PASSWORD and auth != expected:
        return False
    return True


def _try_decode_payload(conn, payload_hex=None, payload_json=None):
    data = None

    if payload_json:
        try:
            if isinstance(payload_json, dict):
                data = payload_json
            else:
                data = json.loads(payload_json)
        except Exception:
            data = None

    if data is None and payload_hex:
        try:
            raw = bytes.fromhex(payload_hex)
            text = raw.decode("utf-8")
            data = json.loads(text)
        except Exception:
            return None

    if not isinstance(data, dict):
        return None

    battery = data.get("b")
    if battery is None:
        battery = data.get("battery_pct")
    temp = data.get("t")
    if temp is None:
        temp = data.get("temp")
    if temp is None:
        temp = data.get("temperature")
    humidity = data.get("h")
    if humidity is None:
        humidity = data.get("hum")
    if humidity is None:
        humidity = data.get("humidity")
    charging = data.get("ch")
    wake_boots = data.get("wb")
    wake_time_ms = data.get("wt")

    dev_addr = data.get("d")
    if not dev_addr:
        return None

    # Ensure device exists
    conn.execute(
        "INSERT OR IGNORE INTO devices (dev_addr, last_seen) VALUES (?, datetime('now', 'localtime'))",
        (dev_addr,),
    )

    updates = ["last_seen = datetime('now', 'localtime')"]
    params = []

    if data.get("lt") is not None:
        updates.append("lat = ?"); params.append(data["lt"])
    if data.get("ln") is not None:
        updates.append("lon = ?"); params.append(data["ln"])
    if battery is not None:
        updates.append("battery_pct = ?"); params.append(battery)
    if temp is not None:
        updates.append("temperature = ?"); params.append(temp)
    if humidity is not None:
        updates.append("humidity = ?"); params.append(humidity)
    if data.get("hv") is not None:
        updates.append("hw_version = ?"); params.append(data["hv"])
    if data.get("tp") is not None:
        updates.append("device_type = ?"); params.append(data["tp"])
    if data.get("g") is not None and data["g"] == 1:
        updates.append("updated_at = datetime('now', 'localtime')")

    if data.get("g") is not None:
        updates.append("gps_fresh = ?"); params.append(data["g"])

    conn.execute(
        f"UPDATE devices SET {', '.join(updates)} WHERE dev_addr = ?",
        params + [dev_addr],
    )

    print(f"[JSON] Dev={dev_addr} lat={data.get('lt')} lon={data.get('ln')} "
          f"bat={battery}% temp={temp} hum={humidity} ch={charging} wb={wake_boots} wt={wake_time_ms} hw={data.get('hv')} type={data.get('tp')}")
    return {
        "dev_addr": dev_addr,
        "temperature": temp,
        "humidity": humidity,
        "battery": battery,
        "charging": charging,
        "wake_boots": wake_boots,
        "wake_time_ms": wake_time_ms,
        "lat": data.get("lt"),
        "lon": data.get("ln"),
        "device_type": data.get("tp"),
    }


_init_db()
_init_config()


# ── Health ─────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    conn = _get_db()
    total = conn.execute("SELECT COUNT(*) FROM packets").fetchone()[0]
    conn.close()
    return jsonify({
        "status":          "ok",
        "uptime_s":        int(time.time() - started_at),
        "packets_stored":  total,
        "packets_memory":  len(packets),
    })


# ── Ingest ─────────────────────────────────────────────────────────

@app.route("/api/lora/ingest", methods=["POST"])
def ingest():
    if not _check_auth():
        return jsonify({"ok": False, "msg": "No autorizado"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False, "msg": "JSON invalido"}), 400

    pkt = {
        "gateway_id":  data.get("gateway_id", "?"),
        "received_at": data.get("received_at", 0),
        "rssi":        data.get("rssi"),
        "snr":         data.get("snr"),
        "freq_mhz":    data.get("freq_mhz"),
        "sf":          data.get("sf"),
        "payload_hex": data.get("payload_hex", ""),
    }

    lw = data.get("lorawan")
    if lw:
        pkt["lorawan"] = {
            "mtype_str": lw.get("mtype_str"),
            "dev_addr":  lw.get("dev_addr"),
            "fcnt":      lw.get("fcnt"),
        }

    dev_addr = (pkt.get("lorawan") or {}).get("dev_addr")

    conn = _get_db()

    # Intentar decodificar el payload JSON (GPS, bateria, hw, etc.)
    decoded = _try_decode_payload(
        conn,
        data.get("payload_hex", ""),
        data.get("payload_json"),
    )

    # Usar dev_addr del JSON si existe, sino LoRaWAN, sino raw prefix
    if decoded:
        dev_addr = decoded["dev_addr"]
    elif not dev_addr and data.get("payload_hex"):
        dev_addr = "raw-" + data["payload_hex"][:8]

    temperature = decoded.get("temperature") if decoded else None
    humidity = decoded.get("humidity") if decoded else None
    battery = decoded.get("battery") if decoded else None
    charging = decoded.get("charging") if decoded else None
    wake_boots = decoded.get("wake_boots") if decoded else None
    wake_time_ms = decoded.get("wake_time_ms") if decoded else None
    conn.execute("""
        INSERT INTO packets
          (gateway_id, received_at, rssi, snr, freq_mhz, sf,
           payload_hex, dev_addr, temperature, humidity, battery, charging, wake_boots, wake_time_ms, mtype_str, fcnt, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
    """, (
        pkt["gateway_id"],
        pkt["received_at"],
        pkt["rssi"],
        pkt["snr"],
        pkt["freq_mhz"],
        pkt["sf"],
        pkt["payload_hex"],
        dev_addr,
        temperature,
        humidity,
        battery,
        charging,
        wake_boots,
        wake_time_ms,
        (pkt.get("lorawan") or {}).get("mtype_str"),
        (pkt.get("lorawan") or {}).get("fcnt"),
    ))
    # Auto-register unknown gateway
    conn.execute(
        "INSERT OR IGNORE INTO gateways (gateway_id, last_seen) VALUES (?, datetime('now', 'localtime'))",
        (pkt["gateway_id"],),
    )
    conn.execute(
        "UPDATE gateways SET last_seen = datetime('now', 'localtime'), wifi_ip = ? WHERE gateway_id = ?",
        (request.remote_addr, pkt["gateway_id"]),
    )
    if dev_addr:
        conn.execute(
            "INSERT OR IGNORE INTO devices (dev_addr, last_seen) VALUES (?, datetime('now', 'localtime'))",
            (dev_addr,),
        )
        conn.execute(
            "UPDATE devices SET last_seen = datetime('now', 'localtime'), wifi_ip = ? WHERE dev_addr = ?",
            (request.remote_addr, dev_addr),
        )

    conn.commit()
    conn.close()

    with lock:
        packets.appendleft(pkt)

    gw    = pkt["gateway_id"]
    rssi  = pkt["rssi"]
    snr   = pkt["snr"]
    dev   = dev_addr or "-"
    mtype = (pkt.get("lorawan") or {}).get("mtype_str", "raw")

    print(f"[INGEST] GW={gw}  RSSI={rssi}  SNR={snr}  "
          f"Dev={dev}  type={mtype}  stored=#{len(packets)}")

    return jsonify({"ok": True}), 200


# ── Packets ────────────────────────────────────────────────────────

@app.route("/api/packets", methods=["GET"])
def list_packets():
    limit   = request.args.get("limit", 50, type=int)
    offset  = request.args.get("offset", 0, type=int)
    gateway = request.args.get("gateway", None)
    dev     = request.args.get("dev", None)
    mtype   = request.args.get("mtype", None)

    where  = []
    params = []
    if gateway:
        where.append("gateway_id = ?")
        params.append(gateway)
    if dev:
        where.append("dev_addr = ?")
        params.append(dev)
    if mtype:
        where.append("mtype_str = ?")
        params.append(mtype)

    sql = "SELECT * FROM packets"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    conn = _get_db()
    rows  = conn.execute(sql, params).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) FROM packets"
        + (" WHERE " + " AND ".join(where) if where else ""),
        params[:-2] if where else [],
    ).fetchone()[0]
    conn.close()

    return jsonify({
        "count":   total,
        "limit":   limit,
        "offset":  offset,
        "packets": [dict(r) for r in rows],
    })


# ── Stats ──────────────────────────────────────────────────────────

@app.route("/api/stats", methods=["GET"])
def stats():
    conn = _get_db()
    total    = conn.execute("SELECT COUNT(*) FROM packets").fetchone()[0]
    gateways = conn.execute(
        "SELECT COUNT(DISTINCT gateway_id) FROM packets"
    ).fetchone()[0]
    devices  = conn.execute(
        "SELECT COUNT(DISTINCT dev_addr) FROM packets WHERE dev_addr IS NOT NULL"
    ).fetchone()[0]
    last     = conn.execute(
        "SELECT * FROM packets ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()

    return jsonify({
        "total_packets":   total,
        "unique_gateways": gateways,
        "unique_devices":  devices,
        "last_packet":     dict(last) if last else None,
    })


# ── Config ─────────────────────────────────────────────────────────

@app.route("/api/config", methods=["GET", "PUT"])
def config():
    if request.method == "GET":
        conn = _get_db()
        rows = conn.execute("SELECT key, value FROM config").fetchall()
        conn.close()
        return jsonify({r["key"]: r["value"] for r in rows})

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False, "msg": "JSON invalido"}), 400

    allowed = {"listen_port", "auth_password", "max_packets"}
    conn = _get_db()
    for k, v in data.items():
        if k not in allowed:
            continue
        conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (k, str(v)),
        )
    conn.commit()
    conn.close()

    _reload_config()
    return jsonify({"ok": True})


# ── Gateway Sync ───────────────────────────────────────────────────

@app.route("/api/lora/gateway/sync", methods=["POST"])
def gateway_sync():
    if not _check_auth():
        return jsonify({"ok": False, "msg": "No autorizado"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False, "msg": "JSON invalido"}), 400

    gw_id = data.get("gateway_id")
    if not gw_id:
        return jsonify({"ok": False, "msg": "gateway_id requerido"}), 400

    conn = _get_db()

    conn.execute(
        "INSERT OR IGNORE INTO gateways (gateway_id) VALUES (?)", (gw_id,)
    )

    updates = ["updated_at = datetime('now', 'localtime')", "last_seen = datetime('now', 'localtime')"]
    params: list = []

    field_map = {
        "name":        "name",
        "lat":         "lat",
        "lon":         "lon",
        "wifi_ssid":   "wifi_ssid",
        "wifi_rssi":   "wifi_rssi",
        "battery_pct": "battery_pct",
        "uptime_s":    "uptime_s",
        "pkts_total":  "pkts_total",
        "wifi_ip":     "wifi_ip",
        # is_paired NO se actualiza desde sync — solo el endpoint /pair lo cambia
    }
    if "pairing_code" in data and data["pairing_code"]:
        field_map["pairing_code"]       = "pairing_code"
        field_map["pairing_expires_at"] = "pairing_expires_at"
    for json_key, col in field_map.items():
        if json_key in data and data[json_key] is not None:
            updates.append(f"{col} = ?")
            params.append(data[json_key])

    conn.execute(
        f"UPDATE gateways SET {', '.join(updates)} WHERE gateway_id = ?",
        params + [gw_id],
    )
    conn.commit()

    row = conn.execute(
        "SELECT name, is_paired FROM gateways WHERE gateway_id = ?", (gw_id,)
    ).fetchone()
    conn.close()

    assigned_name = row["name"] if row else None
    is_paired = bool(row["is_paired"]) if row else False

    print(f"[SYNC] GW={gw_id}  name={data.get('name', '-')}  "
          f"uptime={data.get('uptime_s')}s  pkts={data.get('pkts_total')}  "
          f"wifi={data.get('wifi_ssid', '-')}({data.get('wifi_rssi')}dBm)  "
          f"bat={data.get('battery_pct')}%  "
          f"gps={data.get('lat')},{data.get('lon')}  "
          f"assigned_name={assigned_name or '-'}")

    return jsonify({
        "ok":        True,
        "name":      assigned_name,
        "is_paired": is_paired,
    }), 200


@app.route("/api/lora/gateway/pair", methods=["POST"])
def gateway_pair():
    if not _check_auth():
        return jsonify({"ok": False, "msg": "No autorizado"}), 401

    data = request.get_json(silent=True) or {}
    code = (data.get("pairing_code") or "").strip()
    name = (data.get("name") or "").strip()
    hint_gw_id = (data.get("gateway_id") or "").strip() or None

    if not code:
        return jsonify({"ok": False, "msg": "pairing_code requerido"}), 400

    conn = _get_db()
    row = None
    if hint_gw_id:
        row = conn.execute(
            "SELECT gateway_id, pairing_code, pairing_expires_at, is_paired, name "
            "FROM gateways WHERE gateway_id = ?",
            (hint_gw_id,),
        ).fetchone()
        if row and (row["pairing_code"] or "") != code:
            conn.close()
            return jsonify({"ok": False, "msg": "El codigo no corresponde al gateway seleccionado."}), 403
    if row is None:
        row = conn.execute(
            "SELECT gateway_id, pairing_code, pairing_expires_at, is_paired, name "
            "FROM gateways "
            "WHERE pairing_code = ? AND COALESCE(is_paired, 0) = 0 "
            "AND pairing_expires_at IS NOT NULL "
            "AND datetime(pairing_expires_at) > datetime('now', 'localtime') "
            "ORDER BY pairing_expires_at DESC LIMIT 1",
            (code,),
        ).fetchone()

    if not row:
        conn.close()
        return jsonify({"ok": False, "msg": "Codigo de pairing invalido o expirado."}), 403

    if row["is_paired"]:
        conn.close()
        return jsonify({"ok": False, "msg": "El gateway ya esta registrado."}), 409

    gw_id = row["gateway_id"]
    final_name = name if name else gw_id

    conn.execute(
        """
        UPDATE gateways
           SET is_paired = 1,
               name = ?,
               pairing_code = NULL,
               pairing_expires_at = NULL,
               updated_at = datetime('now', 'localtime'),
               last_seen = datetime('now', 'localtime')
         WHERE gateway_id = ?
        """,
        (final_name, gw_id),
    )
    conn.commit()
    conn.close()

    print(f"[PAIR] GW={gw_id} registrado como '{final_name}'")
    return jsonify({"ok": True, "gateway_id": gw_id, "name": final_name}), 200


# ── Equipment (devices) ────────────────────────────────────────────

@app.route("/api/lora/equipment", methods=["POST"])
def equipment():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False, "msg": "JSON invalido"}), 400

    dev_addr = data.get("dev_addr")
    if not dev_addr:
        return jsonify({"ok": False, "msg": "dev_addr requerido"}), 400

    conn = _get_db()

    updates = ["updated_at = datetime('now', 'localtime')", "last_seen = datetime('now', 'localtime')"]
    params = []

    field_map = {
        "name":           "name",
        "lat":            "lat",
        "lon":            "lon",
        "wifi_ssid":      "wifi_ssid",
        "wifi_rssi":      "wifi_rssi",
        "battery_pct":    "battery_pct",
        "temperature":    "temperature",
        "humidity":       "humidity",
        "device_type":    "device_type",
        "refresh_freq_s": "refresh_freq_s",
        "hw_version":     "hw_version",
        "wifi_ip":        "wifi_ip",
    }
    for json_key, col in field_map.items():
        if json_key in data and data[json_key] is not None:
            updates.append(f"{col} = ?")
            params.append(data[json_key])

    conn.execute(
        "INSERT OR IGNORE INTO devices (dev_addr) VALUES (?)", (dev_addr,)
    )
    conn.execute(
        f"UPDATE devices SET {', '.join(updates)} WHERE dev_addr = ?",
        params + [dev_addr],
    )
    conn.commit()
    row = conn.execute(
        "SELECT name, device_type, refresh_freq_s FROM devices WHERE dev_addr = ?",
        (dev_addr,),
    ).fetchone()
    conn.close()

    cfg = {
        "name": row["name"] if row else None,
        "device_type": row["device_type"] if row else "sensor",
        "refresh_freq_s": row["refresh_freq_s"] if row else 60,
    }

    print(f"[EQUIPMENT] Dev={dev_addr}  name={data.get('name', '-')}  "
          f"lat={data.get('lat')}  lon={data.get('lon')}  "
          f"wifi={data.get('wifi_ssid', '-')}({data.get('wifi_rssi')}dBm)  "
          f"bat={data.get('battery_pct')}%  config={cfg}")

    return jsonify({"ok": True, "config": cfg}), 200


@app.route("/api/lora/device/config", methods=["GET"])
def get_device_config():
    dev_addr = request.args.get("dev_addr")
    if not dev_addr:
        return jsonify({"ok": False, "msg": "dev_addr requerido"}), 400

    conn = _get_db()
    row = conn.execute(
        "SELECT name, device_type, refresh_freq_s FROM devices WHERE dev_addr = ?",
        (dev_addr,),
    ).fetchone()
    conn.close()

    if row:
        return jsonify({
            "ok": True,
            "config": {
                "name": row["name"],
                "device_type": row["device_type"],
                "refresh_freq_s": row["refresh_freq_s"],
            }
        })
    else:
        # Device not registered yet — return defaults
        return jsonify({
            "ok": True,
            "config": {
                "name": None,
                "device_type": "sensor",
                "refresh_freq_s": 60,
            }
        })


# ── Main ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"=== ExaLink LoRaWAN HTTPS Listener ===")
    print(f"  Puerto : {LISTEN_PORT}")
    print(f"  Auth   : {'habilitada' if AUTH_PASSWORD else 'deshabilitada'}")
    print(f"  Buffer : {MAX_PACKETS} paquetes")
    print(f"  DB     : {DB_PATH}")
    print(f"=======================================")

    app.run(
        host="0.0.0.0",
        port=LISTEN_PORT,
        ssl_context=("cert.pem", "key.pem"),
        debug=False,
    )
