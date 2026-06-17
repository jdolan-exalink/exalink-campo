# Arquitectura — Exalink Campo

## Visión General

Plataforma SaaS multi-tenant para gestión ganadera inteligente.
Tres modalidades de operación:

| Modo | Descripción |
|------|-------------|
| Solo Software | CRUD animales, sanidad, reproducción, pesajes |
| Software + IoT | GPS, LoRa, MQTT, alertas en tiempo real |
| Software + IoT + IA | Predicción celo/parto, detección comportamiento |

## Stack Tecnológico

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND                            │
│  React 18 + Vite + TypeScript + Tailwind + Leaflet      │
│  React Query (cache) + Zustand (estado) + RHF (forms)   │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP/REST
┌────────────────────────▼────────────────────────────────┐
│                     BACKEND                             │
│  FastAPI 0.115 + Python 3.13 + SQLAlchemy 2.0 async     │
│  GeoAlchemy2 + Shapely (PostGIS)                        │
│  JWT (python-jose) + bcrypt (passlib)                   │
└──────┬────────────────────────────┬─────────────────────┘
       │ asyncpg                    │ aiomqtt
┌──────▼──────┐           ┌────────▼────────┐
│ PostgreSQL  │           │    Mosquitto    │
│ + PostGIS   │           │    MQTT 2.0     │
└──────┬──────┘           └────────┬────────┘
       │                           │ publish
┌──────▼──────┐           ┌────────▼────────┐
│    Redis    │           │  Dispositivos   │
│  Cache/PS   │           │  GPS + Sensores │
└─────────────┘           └─────────────────┘
```

## Multi-Tenancy

- Isolación por `tenant_id` en todas las tablas
- Roles: `superadmin`, `tenant_admin`, `vet`, `manager`, `operator`, `readonly`
- Un superadmin puede ver todos los tenants desde el NOC

## MQTT Topics

```
exalink/{tenant_slug}/devices/{device_id}/location   ← GPS updates
exalink/{tenant_slug}/devices/{device_id}/status     ← Device status
exalink/{tenant_slug}/commands/{device_id}           → Comandos (beep)
exalink/{tenant_slug}/alerts/{alert_id}             ← Alertas
```

## Payload GPS

```json
{
  "device_id": "COLLAR001",
  "lat": -31.6300,
  "lon": -60.7000,
  "battery": 90,
  "rssi": -80,
  "temperature": 25.4,
  "activity_score": 40,
  "timestamp": "2026-06-08T12:00:00Z"
}
```

## Comandos a Dispositivos

```json
{ "command": "beep_left" }
{ "command": "beep_right" }
{ "command": "beep_warning" }
```

## Sistema de Mapas

| Capa | Fuente | Modo |
|------|--------|------|
| OSM | openstreetmap.org | Online |
| Vectorial | TileServer GL | Self-hosted |
| Satélite | Esri World Imagery | Online (testing) |
| Satélite offline | MapProxy / TileServer GL | Self-hosted |
| Potreros | PostGIS + GeoJSON | DB |
| Martin | PostGIS vector tiles | Self-hosted |

## Modelos de Datos

```
Tenant
  └── User (roles)
  └── Establishment
        └── Paddock (PostGIS POLYGON)
        └── Herd
        └── Animal
              └── Device → Location (PostGIS POINT, time-series)
              └── HealthEvent
              └── ReproductionEvent
              └── WeightRecord
        └── Alert
        └── Geofence (PostGIS POLYGON)
```

## API Endpoints

```
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
GET    /api/v1/auth/me

GET    /api/v1/animals        (paginado, filtros)
POST   /api/v1/animals
GET    /api/v1/animals/{id}
PUT    /api/v1/animals/{id}
DELETE /api/v1/animals/{id}
GET    /api/v1/animals/{id}/track

GET    /api/v1/paddocks
POST   /api/v1/paddocks
GET    /api/v1/paddocks/{id}
PUT    /api/v1/paddocks/{id}

GET    /api/v1/devices
POST   /api/v1/devices
GET    /api/v1/devices/{id}
GET    /api/v1/devices/{id}/track

GET    /api/v1/alerts
POST   /api/v1/alerts
POST   /api/v1/alerts/{id}/resolve
POST   /api/v1/alerts/{id}/acknowledge

GET    /api/v1/dashboard/kpis
GET    /api/v1/dashboard/map-data

GET    /api/v1/health
POST   /api/v1/health
GET    /api/v1/reproduction
POST   /api/v1/reproduction
GET    /api/v1/weights
POST   /api/v1/weights

POST   /api/v1/import/animals
GET    /api/v1/import/template/animals

GET    /api/v1/noc/overview    (superadmin)
GET    /api/v1/noc/devices     (superadmin)
```
