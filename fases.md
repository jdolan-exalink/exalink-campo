# Exalink Campo — Estado del Proyecto por Fases

> Última actualización: 2026-06-08
> 101 archivos · monorepo en `/mnt/SSD/DEVs/ExaCow/`

---

## FASE 0 — Infraestructura Base ✅ COMPLETA

| Item | Archivo | Estado |
|------|---------|--------|
| Docker Compose (postgres, redis, mosquitto, backend, frontend) | `docker-compose.yml` | ✅ |
| TileServer GL y Martin como profiles opcionales | `docker-compose.yml` | ✅ |
| Variables de entorno documentadas | `.env.example` | ✅ |
| Makefile con comandos de operación | `Makefile` | ✅ |
| Init SQL (postgis, uuid-ossp, pg_trgm) | `scripts/init_db.sql` | ✅ |
| Config MQTT Mosquitto | `mosquitto/config/mosquitto.conf` | ✅ |
| Nginx config para frontend | `frontend/nginx.conf` | ✅ |

---

## FASE 1 — Backend Core ✅ COMPLETA

### Configuración y seguridad
| Item | Archivo | Estado |
|------|---------|--------|
| Settings Pydantic (DB, Redis, MQTT, JWT, notificaciones) | `app/core/config.py` | ✅ |
| Engine SQLAlchemy async (asyncpg, pool) | `app/core/database.py` | ✅ |
| JWT access + refresh token | `app/core/security.py` | ✅ |
| Dependency injection (get_db, get_current_user, require_roles) | `app/core/deps.py` | ✅ |
| pyproject.toml con todas las dependencias | `backend/pyproject.toml` | ✅ |
| Dockerfile backend | `backend/Dockerfile` | ✅ |

### Modelos SQLAlchemy 2.0 + PostGIS
| Modelo | Archivo | Estado |
|--------|---------|--------|
| Base / Mixins (UUID, Timestamp, TenantScoped) | `models/base.py` | ✅ |
| Tenant (plan, settings, límites) | `models/tenant.py` | ✅ |
| User (roles enum, tenant_id nullable para superadmin) | `models/user.py` | ✅ |
| Establishment (PostGIS POINT, POLYGON boundary) | `models/establishment.py` | ✅ |
| Herd (rodeo) | `models/herd.py` | ✅ |
| Paddock (PostGIS POLYGON, carga ganadera) | `models/paddock.py` | ✅ |
| Animal (caravana, RFID, raza, categoría, estado) | `models/animal.py` | ✅ |
| Device (collar, caravana, sensor, gateway + PostGIS last_location) | `models/device.py` | ✅ |
| Location (time-series GPS, índices compuestos) | `models/location.py` | ✅ |
| Alert (tipos, severidades, estados) | `models/alert.py` | ✅ |
| HealthEvent (vacuna, tratamiento, enfermedad, etc.) | `models/health.py` | ✅ |
| ReproductionEvent (celo, servicio, IA, tacto, parto) | `models/reproduction.py` | ✅ |
| WeightRecord (pesajes con GDP diario) | `models/weight.py` | ✅ |
| Geofence (PostGIS POLYGON, tipos allowed/forbidden) | `models/geofence.py` | ✅ |

### Migración Alembic
| Item | Archivo | Estado |
|------|---------|--------|
| env.py async (asyncpg) | `alembic/env.py` | ✅ |
| Migración inicial con todas las tablas e índices | `alembic/versions/001_initial_schema.py` | ✅ |

---

## FASE 2 — API REST ✅ COMPLETA (backend)

| Router | Endpoints | Estado |
|--------|-----------|--------|
| Auth | login, refresh, me | ✅ |
| Animals | CRUD + paginación + filtros + track GPS | ✅ |
| Paddocks | CRUD + GeoJSON polygon | ✅ |
| Devices | CRUD + track histórico | ✅ |
| Alerts | list + create + acknowledge + resolve + stats | ✅ |
| Dashboard | /kpis + /map-data | ✅ |
| Establishments | CRUD + contadores | ✅ |
| Health | list + create + delete | ✅ |
| Reproduction | list + create | ✅ |
| Weights | list + create | ✅ |
| Import | POST /animals (Excel/CSV) + GET /template | ✅ |
| NOC | /overview + /devices (solo superadmin) | ✅ |

---

## FASE 3 — IoT / MQTT ✅ COMPLETA (base)

| Item | Archivo | Estado |
|------|---------|--------|
| Consumidor MQTT asíncrono (aiomqtt) | `services/mqtt_consumer.py` | ✅ |
| Subscripción a `exalink/+/devices/+/location` | `services/mqtt_consumer.py` | ✅ |
| Subscripción a `exalink/+/devices/+/status` | `services/mqtt_consumer.py` | ✅ |
| Actualización device (last_location, battery, rssi, temp) | `services/mqtt_consumer.py` | ✅ |
| Persistencia de track en tabla `locations` | `services/mqtt_consumer.py` | ✅ |
| Alerta automática batería ≤ 15% | `services/mqtt_consumer.py` | ✅ |
| Reconexión automática con backoff | `services/mqtt_consumer.py` | ✅ |
| Simulador GPS para desarrollo | `scripts/simulate_gps.py` | ✅ |

---

## FASE 4 — Frontend ✅ COMPLETA (estructura base)

### Infraestructura frontend
| Item | Archivo | Estado |
|------|---------|--------|
| Vite + React 18 + TypeScript | `vite.config.ts`, `tsconfig.json` | ✅ |
| Tailwind CSS con tema Exalink (dark navy/blue/green) | `tailwind.config.ts`, `index.css` | ✅ |
| Path alias `@/` | `vite.config.ts`, `tsconfig.json` | ✅ |
| React Query (cache, stale time, refetch interval) | `main.tsx` | ✅ |
| Zustand auth store (persist + refresh token auto) | `store/authStore.ts` | ✅ |
| Axios con interceptor JWT + refresh automático | `lib/api.ts` | ✅ |
| Tipos TypeScript completos | `types/index.ts` | ✅ |
| Utilidades (formatDate, timeAgo, colores semánticos) | `lib/utils.ts` | ✅ |
| React Hot Toast | `main.tsx` | ✅ |

### Layout
| Componente | Archivo | Estado |
|------------|---------|--------|
| MainLayout (sidebar + outlet) | `components/layout/MainLayout.tsx` | ✅ |
| Sidebar con navegación, roles, logout | `components/layout/Sidebar.tsx` | ✅ |
| Header con alertas activas en tiempo real | `components/layout/Header.tsx` | ✅ |

### Componentes
| Componente | Archivo | Estado |
|------------|---------|--------|
| KPICard (ícono, valor, color semántico, alerta visual) | `components/dashboard/KPICard.tsx` | ✅ |
| AlertsFeed (feed en vivo, polling 15s) | `components/dashboard/AlertsFeed.tsx` | ✅ |
| LiveMap (Leaflet + 3 capas + polígonos + markers) | `components/map/LiveMap.tsx` | ✅ |
| LayerControl integrado en LiveMap | `components/map/LiveMap.tsx` | ✅ |

### Páginas
| Página | Archivo | Estado | Observaciones |
|--------|---------|--------|---------------|
| Login | `pages/Login.tsx` | ✅ | Con credenciales demo precompletadas |
| Dashboard | `pages/Dashboard.tsx` | ✅ | KPIs + mapa + alertas + stats |
| Animals | `pages/Animals.tsx` | ✅ | Tabla paginada, filtros, descarga plantilla |
| Paddocks | `pages/Paddocks.tsx` | ✅ | Cards + editor de polígono por puntos con arrastre de vértices |
| PaddockMapEditor | `components/map/PaddockMapEditor.tsx` | ✅ | Dibujo por clic, undo, edición arrastrando vértices, cálculo de área |
| PaddockFormModal | `components/paddocks/PaddockFormModal.tsx` | ✅ | Modal con form + mapa integrado para crear/editar |
| Devices | `pages/Devices.tsx` | ✅ | Tabla con barra de batería, estado online/offline |
| Alerts | `pages/Alerts.tsx` | ✅ | Filtros, acknowledge, resolve |
| Health | `pages/Health.tsx` | ✅ | Tabla historial sanitario |
| Reproduction | `pages/Reproduction.tsx` | ✅ | Tabla eventos reproductivos |
| Weights | `pages/Weights.tsx` | ✅ | Tabla pesajes con GDP |
| MapPage | `pages/MapPage.tsx` | ✅ | Mapa fullscreen |
| NOC | `pages/NOC.tsx` | ✅ | Vista superadmin (tenants + devices) |

---

## FASE 5 — Datos Demo ✅ COMPLETA

| Item | Archivo | Estado |
|------|---------|--------|
| 1 Tenant "Establecimiento Demo" | `scripts/seed_demo.py` | ✅ |
| SuperAdmin + Tenant Admin | `scripts/seed_demo.py` | ✅ |
| 1 Establecimiento en Santa Fe, Argentina | `scripts/seed_demo.py` | ✅ |
| 4 Potreros con polígonos PostGIS reales | `scripts/seed_demo.py` | ✅ |
| 1 Rodeo | `scripts/seed_demo.py` | ✅ |
| 50 Animales (40 hembras, 10 machos, múltiples razas) | `scripts/seed_demo.py` | ✅ |
| 10 Collares GPS asignados a animales | `scripts/seed_demo.py` | ✅ |
| 1 Gateway | `scripts/seed_demo.py` | ✅ |
| 100 puntos GPS históricos (10 por collar) | `scripts/seed_demo.py` | ✅ |
| 5 Alertas demo (batería, geocerca, offline, celo, parto) | `scripts/seed_demo.py` | ✅ |
| 10 Eventos sanitarios | `scripts/seed_demo.py` | ✅ |
| 5 Pesajes con GDP | `scripts/seed_demo.py` | ✅ |
| 5 Eventos reproductivos | `scripts/seed_demo.py` | ✅ |

---

## FASE 6 — Documentación ✅ COMPLETA (base)

| Documento | Archivo | Estado |
|-----------|---------|--------|
| README con quickstart, servicios, estructura | `README.md` | ✅ |
| Arquitectura (diagramas, stack, API, MQTT topics) | `docs/architecture.md` | ✅ |
| Roadmap técnico v0.1 → v1.0 | `docs/roadmap.md` | ✅ |
| Fases del proyecto | `fases.md` | ✅ |

---

---

# LO QUE FALTA — Por Fase

## FASE 7 — Formularios CRUD Frontend ❌ PENDIENTE

Los modelos y APIs existen, pero el frontend solo tiene vistas de lectura.
Falta implementar los modales/formularios de alta, edición y eliminación.

| Item | Prioridad |
|------|-----------|
| Modal crear/editar Animal (form completo con validación Zod) | 🔴 Alta |
| Modal crear/editar Potrero con editor de polígono en mapa | 🔴 Alta |
| Modal crear/editar Establecimiento | 🔴 Alta |
| Modal asignar Dispositivo a Animal | 🔴 Alta |
| Modal crear Evento Sanitario | 🟡 Media |
| Modal crear Evento Reproductivo | 🟡 Media |
| Modal crear Pesaje | 🟡 Media |
| Modal crear Alerta manual | 🟡 Media |
| Gestión de Rodeos (CRUD) | 🟡 Media |
| Panel de gestión de Usuarios por tenant | 🟡 Media |
| Panel de gestión de Tenants (superadmin) | 🟡 Media |

---

## FASE 8 — Importación Masiva Completa ❌ PENDIENTE

La API de importación existe, pero la UI está incompleta.

| Item | Prioridad |
|------|-----------|
| Modal ImportModal con drag & drop de archivo | 🔴 Alta |
| Preview de datos antes de confirmar importación | 🔴 Alta |
| Reporte de errores por fila | 🔴 Alta |
| Importación masiva de Pesajes (Excel) | 🟡 Media |
| Importación masiva de Eventos Sanitarios | 🟡 Media |
| Importación masiva de Dispositivos | 🟡 Media |

---

## FASE 9 — Exportación ❌ PENDIENTE

No implementado. Las APIs de lectura están listas para generar reportes.

| Item | Prioridad |
|------|-----------|
| Exportar listado de Animales a Excel | 🔴 Alta |
| Exportar historial sanitario a Excel/PDF | 🔴 Alta |
| Exportar historial de pesajes a Excel | 🔴 Alta |
| Exportar trayectorias GPS a KML/GPX | 🟡 Media |
| Reportes PDF (sanidad por rodeo, movimientos) | 🟡 Media |
| Servicio backend `export_service.py` (openpyxl, reportlab) | 🟡 Media |

---

## FASE 10 — Tiempo Real con WebSocket ❌ PENDIENTE

El mapa usa polling HTTP (15s). Para producción se necesita WebSocket.

| Item | Prioridad |
|------|-----------|
| Endpoint WebSocket `/ws/{tenant_id}` en FastAPI | 🔴 Alta |
| Redis Pub/Sub como bus de eventos internos | 🔴 Alta |
| MQTT consumer publica en Redis → FastAPI reenvía por WS | 🔴 Alta |
| Frontend hook `useWebSocket` para mapa en vivo | 🔴 Alta |
| Trails de recorrido en tiempo real en el mapa | 🟡 Media |
| Notificaciones push de alertas sin polling | 🟡 Media |

---

## FASE 11 — Geocercas Editor Visual ❌ PENDIENTE

El modelo `Geofence` existe en la DB y la API base está en la migración.
Falta el router API y el editor visual en el mapa.

| Item | Prioridad |
|------|-----------|
| Router API CRUD `/geocercas` | 🔴 Alta |
| Editor de polígonos en mapa (Leaflet.draw o leaflet-geoman) | 🔴 Alta |
| Página Geofences en frontend | 🔴 Alta |
| Detección de salida de geocerca en MQTT consumer | 🔴 Alta |
| Alerta automática `outside_geofence` con PostGIS ST_Within | 🔴 Alta |
| Visualización de geocercas en Dashboard y MapPage | 🟡 Media |

---

## FASE 12 — Alertas Avanzadas (MQTT) ❌ PENDIENTE

El consumer solo detecta batería baja. Faltan los demás tipos.

| Item | Prioridad |
|------|-----------|
| Alerta inmóvil (animal sin movimiento > N minutos) | 🔴 Alta |
| Alerta dispositivo offline (sin señal > N minutos) | 🔴 Alta |
| Alerta fuera de geocerca (PostGIS ST_Within) | 🔴 Alta |
| Alerta temperatura alta (sensor > umbral) | 🟡 Media |
| Alerta actividad anormal (score fuera de rango) | 🟡 Media |
| Predicción celo por actividad elevada sostenida | 🟠 Baja |
| Predicción parto por fecha esperada + comportamiento | 🟠 Baja |
| Servicio `alert_service.py` desacoplado | 🟡 Media |

---

## FASE 13 — Notificaciones ❌ PENDIENTE

Las credenciales están en el `.env`, pero no hay implementación.

| Item | Prioridad |
|------|-----------|
| Servicio `notification_service.py` | 🔴 Alta |
| Notificación WhatsApp via Evolution API | 🟡 Media |
| Notificación Telegram (Bot API) | 🟡 Media |
| Notificación email SMTP (alerta crítica) | 🟡 Media |
| Cola de notificaciones con Redis (evitar spam) | 🟡 Media |
| Configuración de notificaciones por tenant (qué alertas, qué canal) | 🟡 Media |

---

## FASE 14 — Mapas Self-Hosted Completos ❌ PENDIENTE

TileServer GL está en el docker-compose pero solo como profile opcional.

| Item | Prioridad |
|------|-----------|
| Documentación para descargar MBTiles de Argentina | 🔴 Alta |
| Script `scripts/download_tiles.sh` para región configurable | 🟡 Media |
| MapProxy para cachear satélite (Esri) offline | 🟡 Media |
| Martin integrado con PostGIS (vector tiles de potreros/geocercas) | 🟡 Media |
| Capa GeoTIFF propio (Sentinel-2, Landsat, IGN) | 🟠 Baja |
| Layer control expandido en frontend (5 capas configurables) | 🟡 Media |

---

## FASE 15 — Comandos a Dispositivos ❌ PENDIENTE

La arquitectura MQTT está lista para publicar, falta la UI y el servicio.

| Item | Prioridad |
|------|-----------|
| Endpoint `POST /devices/{id}/command` | 🟡 Media |
| Publicar en `exalink/{tenant}/commands/{device_id}` | 🟡 Media |
| UI: botones de guiado sonoro en panel de dispositivo | 🟡 Media |
| Payloads: `beep_left`, `beep_right`, `beep_warning` | 🟡 Media |
| Confirmación de recepción del comando | 🟠 Baja |

---

## FASE 16 — Gestión de Firmware OTA ❌ PENDIENTE

| Item | Prioridad |
|------|-----------|
| Modelo `FirmwareRelease` | 🟠 Baja |
| Endpoint upload firmware | 🟠 Baja |
| Comando OTA por MQTT | 🟠 Baja |
| Estado de actualización en NOC | 🟠 Baja |

---

## FASE 17 — App Móvil ❌ PENDIENTE

| Item | Prioridad |
|------|-----------|
| React Native (Expo) con mismo design system | 🟠 Baja |
| Modo offline con SQLite local | 🟠 Baja |
| Sync bidireccional con backend | 🟠 Baja |
| Scanner RFID/QR por cámara | 🟠 Baja |

---

## FASE 18 — IA y Predicciones ❌ PENDIENTE

| Item | Prioridad |
|------|-----------|
| Worker de análisis de actividad acelerómetro | 🟠 Baja |
| Modelo ML predicción celo (serie temporal actividad) | 🟠 Baja |
| Modelo ML predicción parto (días + comportamiento) | 🟠 Baja |
| Detección anomalías (Isolation Forest o similar) | 🟠 Baja |
| Análisis uso de pasturas por zona (heatmap) | 🟠 Baja |

---

## FASE 19 — Integraciones Externas ❌ PENDIENTE

| Item | Prioridad |
|------|-----------|
| API SENASA (consulta RENSPA, DITs) | 🟠 Baja |
| Integración Odoo (módulo ganadero) | 🟠 Baja |
| Lectores RFID (USB/Bluetooth) | 🟠 Baja |
| Balanzas electrónicas | 🟠 Baja |
| Estaciones meteorológicas | 🟠 Baja |
| Sensores de agua y nivel | 🟠 Baja |
| Cámaras con Frigate (detección de animales) | 🟠 Baja |

---

## FASE 20 — Producción y DevOps ❌ PENDIENTE

| Item | Prioridad |
|------|-----------|
| `docker-compose.prod.yml` con configuración de producción | 🔴 Alta |
| Nginx reverse proxy global (HTTPS, SSL/TLS) | 🔴 Alta |
| Variables de entorno de producción (secrets) | 🔴 Alta |
| Backups automáticos PostgreSQL a S3/minio | 🟡 Media |
| Monitoreo con Prometheus + Grafana | 🟡 Media |
| Logging centralizado (Loki o ELK) | 🟡 Media |
| Health checks más robustos | 🟡 Media |
| Rate limiting en API | 🟡 Media |
| CI/CD con GitHub Actions | 🟡 Media |
| Helm chart para Kubernetes | 🟠 Baja |

---

## Resumen de Prioridades

| Prioridad | Cantidad | Descripción |
|-----------|----------|-------------|
| 🔴 Alta | ~25 items | Necesario para uso real en campo |
| 🟡 Media | ~30 items | Importante para producto completo |
| 🟠 Baja | ~25 items | Diferenciadores y versiones futuras |

### Próximos 3 pasos recomendados

1. **FASE 7** — Formularios CRUD frontend (sin esto el producto no es usable)
2. **FASE 10** — WebSocket para mapa en vivo real (el polling es temporal)
3. **FASE 11** — Editor de geocercas + detección PostGIS (feature central de IoT)

---

## Leyenda

| Símbolo | Significado |
|---------|-------------|
| ✅ | Implementado y funcional |
| ❌ | No implementado |
| 🔴 Alta | Crítico para MVP productivo |
| 🟡 Media | Importante, segunda iteración |
| 🟠 Baja | Diferenciador, versiones futuras |
