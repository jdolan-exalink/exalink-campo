#!/bin/sh
# Entrypoint del backend: asegura el schema y el seed antes de levantar uvicorn.
#   1. Espera a que postgres acepte conexiones.
#   2. alembic upgrade head  (idempotente: no-op si ya está al día).
#   3. Si no hay usuarios (primer despliegue / BD nueva) corre seed_demo.py.
#   4. exec uvicorn.
set -e

echo "[entrypoint] esperando a postgres..."
python - <<'PY'
import os, time, asyncio, asyncpg
url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
async def main():
    for i in range(60):
        try:
            conn = await asyncpg.connect(url)
            await conn.close()
            return
        except Exception:
            time.sleep(1)
    raise SystemExit("[entrypoint] postgres no disponible tras 60s")
asyncio.run(main())
PY
echo "[entrypoint] postgres OK"

echo "[entrypoint] aplicando migraciones (alembic upgrade head)..."
alembic upgrade head
echo "[entrypoint] migraciones OK"

echo "[entrypoint] verificando si hace falta seed..."
NEED_SEED=$(python - <<'PY'
import os, asyncio, asyncpg
url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
async def main():
    try:
        conn = await asyncpg.connect(url)
        try:
            return await conn.fetchval("SELECT count(*) FROM users") or 0
        finally:
            await conn.close()
    except Exception:
        return 0
print("1" if asyncio.run(main()) == 0 else "0")
PY
)

if [ "$NEED_SEED" = "1" ] && [ -f /app/scripts/seed_demo.py ]; then
  echo "[entrypoint] BD sin usuarios -> corriendo seed_demo..."
  python /app/scripts/seed_demo.py || echo "[entrypoint] seed_demo fallo (no critico)"
else
  echo "[entrypoint] seed omitido (ya hay datos o no hay script)"
fi

echo "[entrypoint] arrancando uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
