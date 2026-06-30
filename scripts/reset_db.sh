#!/usr/bin/env bash
#
# RESET TOTAL de la base de datos (sólo si estás dispuesto a perder los datos
# de negocio: usuarios, animales, dispositivos de la BD principal).
#
# Conserva el volumen de LoRa (lora_data: pairings de gateways/clientes).
#
# Qué hace:
#   1. Limpia backend/alembic/versions para que coincida con git (saca duplicados).
#   2. Rebuild + up de todos los servicios.
#   3. DROP + CREATE del schema public (borra todas las tablas + alembic_version,
#      recrea las extensiones postgis/uuid-ossp/pg_trgm).
#   4. alembic upgrade head (crea todo desde cero, hasta la 005).
#   5. seed_demo.py (crea tenant, admin, animales, etc. de prueba).
#
# Uso:  bash scripts/reset_db.sh
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

PGUSER="${POSTGRES_USER:-exalink}"
PGDB="${POSTGRES_DB:-exalink_campo}"

echo "==> 1/5 Sincronizando backend/alembic/versions con git"
git checkout -- backend/alembic/versions 2>/dev/null || true
for f in backend/alembic/versions/*.py; do
  [ -e "$f" ] || continue
  if ! git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
    echo "    - borrando duplicado suelto: $(basename "$f")"
    rm -f "$f"
  fi
done

echo "==> 2/5 Rebuild + up de servicios"
docker compose build
docker compose up -d

echo "    esperando a postgres..."
until docker compose exec -T postgres pg_isready -U "$PGUSER" >/dev/null 2>&1; do
  sleep 1
done
sleep 2

echo "==> 3/5 RESET del schema public (se pierden los datos de la BD principal)"
docker compose exec -T postgres psql -U "$PGUSER" -d "$PGDB" <<'SQL'
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
GRANT ALL ON SCHEMA public TO public;
SQL

echo "==> 4/5 Migraciones desde cero (alembic upgrade head)"
docker compose exec -T backend alembic heads
docker compose exec -T backend alembic upgrade head

echo "==> 5/5 Seed de datos demo (tenant + admin + animales)"
docker compose exec -T backend python /app/scripts/seed_demo.py

echo ""
echo "==> Listo. Login: admin@exalink.com / exalink2024"
echo "    Si el login sigue dando 500, el problema NO es la BD:"
echo "    corré:  docker compose logs --tail=120 backend"
