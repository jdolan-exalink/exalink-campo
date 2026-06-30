#!/usr/bin/env bash
#
# Redeploy limpio y definitivo.
#
# Resuelve de una vez el problema de "Multiple head revisions" / tablas faltantes:
#   1. Fuerza backend/alembic/versions a ser EXACTAMENTE el de origin/master
#      (borra todo y restaura desde git → elimina cualquier duplicado, trackeado o no).
#   2. Rebuild backend (con fallback --no-cache si quedó cache stale).
#   3. Verifica que haya un solo head.
#   4. Resetea el schema public (tablas + alembic_version).
#   5. alembic upgrade head (crea TODAS las tablas desde cero).
#   6. seed_demo (admin + datos demo).
#
# Uso:  bash scripts/redeploy_clean.sh
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

PGUSER="${POSTGRES_USER:-exalink}"
PGDB="${POSTGRES_DB:-exalink_campo}"

echo "==> 1/7 Forzar backend/alembic/versions = origin/master"
git fetch origin master
rm -f backend/alembic/versions/*.py
git checkout origin/master -- backend/alembic/versions
echo "    migraciones presentes:"
ls -1 backend/alembic/versions/*.py | xargs -n1 basename | sed 's/^/      /'

echo "==> 2/7 Rebuild + restart backend"
docker compose build backend
docker compose up -d --force-recreate backend postgres
sleep 3

echo "==> 3/7 Verificar heads (debe ser 1 solo = 005)"
if ! docker compose exec -T backend alembic heads 2>&1 | tee /tmp/_heads.txt; then
  echo "    >>> aún hay múltiples heads. Rebuild SIN cache (puede tardar)..."
  docker compose build --no-cache backend
  docker compose up -d --force-recreate backend
  sleep 3
fi
echo "    heads ahora:"
docker compose exec -T backend alembic heads
HEADS_COUNT=$(docker compose exec -T backend alembic heads 2>/dev/null | grep -c "005" || true)
if [ "$HEADS_COUNT" -ne 1 ]; then
  echo "    >>> ERROR: sigue habiendo múltiples heads. Mostrando versiones:"
  docker compose exec -T backend sh -c 'grep -H "^revision\|^down_revision" alembic/versions/*.py'
  echo "    >>> Pegá esta salida arriba para diagnosticar."
  exit 1
fi

echo "==> 4/7 Reset schema public (fresh)"
until docker compose exec -T postgres pg_isready -U "$PGUSER" >/dev/null 2>&1; do sleep 1; done
docker compose exec -T postgres psql -U "$PGUSER" -d "$PGDB" <<'SQL'
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
GRANT ALL ON SCHEMA public TO public;
SQL

echo "==> 5/7 alembic upgrade head (crea todas las tablas desde cero)"
docker compose exec -T backend alembic upgrade head

echo "==> 6/7 Verificar tablas críticas"
docker compose exec -T postgres psql -U "$PGUSER" -d "$PGDB" -c "\dt" \
  | grep -E "users|alerts|alert_configs|devices|animals" || true

echo "==> 7/7 Seed demo"
docker compose exec -T backend python /app/scripts/seed_demo.py

echo ""
echo "==> Listo. Login: admin@exalink.com / exalink2024"
