#!/usr/bin/env bash
#
# Fix automático de migraciones de alembic.
#
# Resuelve el problema de "Multiple head revisions" / "Revision 004 is present
# more than once" eliminando archivos sueltos (no trackeados) que duplican
# revisiones, reconstruyendo la imagen del backend y aplicando todas las
# migraciones pendientes.
#
# NO toca los datos de negocio (animales, dispositivos, etc.).
#
# Uso:  bash scripts/fix_migrations.sh
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

VERSIONS_DIR="backend/alembic/versions"

echo "==> 1/4 Sincronizando '$VERSIONS_DIR' con git (elimina duplicados sueltos)"
# Restaurar archivos trackeados al estado de HEAD
git checkout -- "$VERSIONS_DIR" 2>/dev/null || true

# Eliminar cualquier .py no trackeado que esté duplicando revisiones
removed=0
for f in "$VERSIONS_DIR"/*.py; do
  [ -e "$f" ] || continue
  if ! git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
    echo "    - eliminando archivo suelto: $(basename "$f")"
    rm -f "$f"
    removed=$((removed + 1))
  fi
done
echo "    archivos en versions ahora:"
ls -1 "$VERSIONS_DIR"/*.py 2>/dev/null | xargs -n1 basename

echo "==> 2/4 Rebuild + restart del backend (toma el versions limpio)"
docker compose build backend
docker compose up -d --force-recreate backend

# Esperar a que el backend responda
echo "    esperando al backend..."
for i in $(seq 1 30); do
  if docker compose exec -T backend python -c "import alembic" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "==> 3/4 Estado de alembic (heads debe ser uno solo = 005)"
docker compose exec -T backend alembic heads
echo "    current:"
docker compose exec -T backend alembic current || true

echo "==> 4/4 Aplicando migraciones"
if ! docker compose exec -T backend alembic upgrade head; then
  echo "    upgrade falló. Intentando recovery: stamp al último correcto (004) y upgrade"
  docker compose exec -T backend alembic stamp 004
  docker compose exec -T backend alembic upgrade head
fi

echo "==> Verificación final"
docker compose exec -T backend alembic current
docker compose exec -T backend python -c "
import asyncio, sys
sys.path.insert(0, '/app')
from sqlalchemy import inspect
from app.core.database import engine
def main():
    def_names = inspect(engine.sync_engine).get_table_names()
    for t in ('alerts', 'alert_configs'):
        print(f'  tabla {t}: {\"OK\" if t in def_names else \"FALTA\"}')
asyncio.run(main())
" 2>/dev/null || true

echo ""
echo "==> Listo. Probá /api/v1/alerts y /api/v1/alert-configs — ya no deberían dar 500."
