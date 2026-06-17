# Exalink Campo — Plataforma Ganadera Inteligente

Plataforma SaaS multi-tenant para gestión integral de establecimientos ganaderos.
Trazabilidad, GPS, IoT, sanidad, reproducción, pesajes y analítica.

## Inicio rápido

```bash
# 1. Configurar variables de entorno
cp .env.example .env

# 2. Levantar todo con un comando
make setup

# 3. Acceder
# Frontend:  http://localhost:3000
# API Docs:  http://localhost:8000/docs
# MQTT:      localhost:1883

# Credenciales demo
# admin@exalink.com / exalink2024
# superadmin@exalink.com / exalink2024
```

## Servicios

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| Frontend | 3000 | React + Tailwind |
| Backend | 8000 | FastAPI + Docs |
| PostgreSQL | 5432 | PostGIS |
| Redis | 6379 | Cache |
| Mosquitto | 1883 | MQTT broker |
| Mosquitto WS | 9001 | WebSocket MQTT |
| TileServer GL | 8081 | Mapas self-hosted (profile: tiles) |

## Comandos útiles

```bash
make up            # Levantar servicios
make down          # Detener servicios
make logs          # Ver logs
make migrate       # Correr migraciones
make seed          # Crear datos demo
make shell-backend # Shell en el backend
make shell-db      # psql en la DB

# Simular GPS (en otra terminal, dev)
python scripts/simulate_gps.py
```

## Estructura

```
exalink-campo/
├── backend/          FastAPI + SQLAlchemy + GeoAlchemy2
│   ├── app/
│   │   ├── api/v1/   Endpoints REST
│   │   ├── models/   SQLAlchemy models (PostGIS)
│   │   ├── schemas/  Pydantic schemas
│   │   ├── services/ MQTT consumer, alertas
│   │   └── core/     Config, DB, seguridad
│   └── alembic/      Migraciones DB
├── frontend/         React + Vite + TypeScript
│   └── src/
│       ├── pages/    Dashboard, Animals, Map, etc.
│       ├── components/
│       └── store/    Zustand
├── scripts/          Seed demo, simulador GPS
├── mosquitto/        Configuración MQTT
├── tiles/            MBTiles para TileServer GL
└── docs/             Arquitectura y roadmap
```

## Capas de mapa disponibles

1. **OpenStreetMap** — caminos y establecimientos (online)
2. **TileServer GL** — vectorial self-hosted (docker profile: tiles)
3. **Esri World Imagery** — satélite para pruebas (online)
4. **Satélite offline** — agregar MBTiles en `./tiles/`

### Satélite offline (opcional)

```bash
# Agregar archivos .mbtiles a ./tiles/
# Iniciar TileServer con el profile tiles
docker compose --profile tiles up tileserver
# Acceder: http://localhost:8081
```

## Payload MQTT GPS

```json
{
  "device_id": "COLLAR001",
  "lat": -31.63,
  "lon": -60.70,
  "battery": 90,
  "rssi": -80,
  "temperature": 25.4,
  "activity_score": 40,
  "timestamp": "2026-06-08T12:00:00Z"
}
```

Topic: `exalink/{tenant_slug}/devices/{device_id}/location`

## Tech Stack

**Backend:** FastAPI · Python 3.13 · SQLAlchemy 2.0 async · GeoAlchemy2 · Alembic · aiomqtt  
**DB:** PostgreSQL 16 + PostGIS 3.4 · Redis 7  
**Broker:** Eclipse Mosquitto 2.0  
**Frontend:** React 18 · Vite · TypeScript · Tailwind CSS · React Leaflet · Zustand · React Query  
**Mapas:** Leaflet · OpenStreetMap · TileServer GL · Esri (testing)  
**Exportación:** openpyxl · pandas  
