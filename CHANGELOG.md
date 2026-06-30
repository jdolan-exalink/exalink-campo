# Changelog

Todos los cambios notables de Exalink Campo se documentan acá.

## [0.2.1] - 2026-06-30

### Fixed
- **Pairing LoRa:** bug de zona horaria (UTC vs localtime) que hacía que un código expirado pareciera vigente en zonas UTC-3. Se estampa `pairing_expires_at` siempre en UTC y se compara contra `datetime('now')` (UTC). TTL configurable vía `PAIRING_TTL_MIN` (default 30 min, antes hardcodeado en 10).
- **Pairing LoRa:** auto-renovación del código en cada `/gateway/sync` mientras el GW siga pending (`PAIRING_AUTO_RENEW=True` por default). Resuelve el "gateway pendiente de registro" tras un reset.
- **Pairing LoRa:** nuevo audit log `pairing_attempts` con IP, user-agent, user_id, código intentado y motivo. Accesible vía `GET /lora/pairing/attempts` (admin).
- **Pairing LoRa:** códigos de error distintos en `/lora/gateways/pair` y `/lora/devices/pair` (`invalid`, `expired`, `mismatch`, `already_paired`, `throttled`, `ok`) para que el front muestre mensajes específicos.
- **Pairing LoRa:** nuevos endpoints admin `POST /lora/gateways/{gw_id}/pairing/{refresh,regenerate,accept-code}`. `accept-code` resuelve el caso "ESP32 reseteó, primer sync todavía no llegó" — el admin, mirando el GW por USB, le dice al server qué código ve en pantalla.
- **Pairing ESP32:** logs estructurados en `provision.py` (lookup, claim, reset) con email del usuario, IP y UA.
- **Clear/Reset:** `/lora/clear` ya NO borra gateways ni devices — solo packets, y requiere admin. Nuevos endpoints admin `/lora/clear/gateways`, `/lora/clear/devices` (rechazan si hay filas paired) y `/lora/reset` (wipe total, requiere `{"confirm": true}`). Tabla `clear_snapshots` con `INSERT OR IGNORE`-restore para poder deshacer.
- **Ingest:** con `LORA_REQUIRE_PAIRING=True` (default), `/lora/ingest` descarta packets de devices no pareados (excepto `gw:*`). El device se auto-registra igual para que aparezca en `/lora/devices/pending`. El response ahora trae `{ok, stored, reason, dev_addr}`.
- **Devices pending:** `/lora/devices/pending` ahora lista TODOS los no-paired, incluyendo los `raw-XXXX` auto-registrados. Cada uno trae `pairing_state` (`awaiting_code` / `code_active` / `code_expired`) y contadores `packets_last_hour` / `packets_total`.
- **DELETE devices/gateways:** ahora admin-only. `?force=true` borra aunque esté paired y limpia packets asociados; sin force, rechaza con `is_paired` y mensaje claro. El frontend en `Lora.tsx` ya manda `?force=true` y muestra el mensaje real del backend en el toast.
- **Migrations Alembic:** encadenadas `004 → 005 → 006` (antes había dos archivos con `revision="004"`, el backend entraba en bucle de reinicio). Quitada columna `color` duplicada en `001_initial_schema` y `add_column` redundante en `003_fields_zones`. Seed de `alert_configs` reescrito para asyncpg (que no acepta múltiples sentencias en un solo `op.execute`).

### Security
- Endpoints destructivos (`/lora/clear*`, `/lora/reset`, `DELETE` devices/gateways) requieren rol `TENANT_ADMIN` o `SUPERADMIN`.
- Rate-limit de intentos de pairing por (target_id, IP): `PAIRING_MAX_ATTEMPTS=10` por `PAIRING_RATE_WINDOW_S=60` por defecto. Configurable.
- El audit log de pairing incluye el `user_id` del JWT cuando el intento viene autenticado, así se puede rastrear quién intentó cada código.

## [0.2.0]

- Sistema de pairing LoRa (gateways y devices) con códigos de 6 dígitos.
- Migrations Alembic iniciales.
- Provisioning ESP32 con códigos `XXXX-XXXX`.
- Sistema de alertas configurable.

## [0.1.0]

- Release inicial: tracking GPS, sensores (temperatura, humedad, batería), geofencing, panel de animales.
