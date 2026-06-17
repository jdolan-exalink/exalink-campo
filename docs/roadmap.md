# Roadmap Técnico — Exalink Campo

## v0.1 — MVP (actual)
- [x] Monorepo Docker Compose
- [x] Backend FastAPI + PostgreSQL/PostGIS
- [x] Multi-tenant con roles
- [x] JWT auth (access + refresh token)
- [x] CRUD Animales (paginado, filtros, importación Excel)
- [x] CRUD Potreros con polígonos GeoJSON
- [x] Gestión dispositivos GPS
- [x] Consumidor MQTT (ubicaciones en tiempo real)
- [x] Sistema de alertas (batería, offline)
- [x] Dashboard con KPIs + mapa Leaflet
- [x] Capas: OSM, Esri, TileServer GL
- [x] NOC básico (vista superadmin)
- [x] Datos demo (50 animales, 10 collares, 4 potreros)
- [x] Simulador GPS MQTT

## v0.2 — Mejoras Core
- [ ] WebSocket para mapa en tiempo real (sin polling)
- [ ] Geocercas editor visual en el mapa
- [ ] Tracking en vivo con trails en el mapa
- [ ] Formularios CRUD completos en frontend
- [ ] Exportación Excel/PDF (animales, sanidad, pesajes)
- [ ] Importación masiva con validación y preview
- [ ] Notificaciones WhatsApp via Evolution API
- [ ] Notificaciones Telegram
- [ ] Notificaciones email SMTP

## v0.3 — IoT Avanzado
- [ ] LoRaWAN gateway support
- [ ] Multi-gateway con cobertura visual en mapa
- [ ] Gestión firmware OTA
- [ ] Comandos a dispositivos (beep, configuración)
- [ ] Dashboard energía (batería por zona)
- [ ] Alertas inmóvil (detección por inactividad GPS)
- [ ] Historial de recorridos completo
- [ ] Exportación KML/GPX de trayectorias

## v0.4 — IA y Predicciones
- [ ] Predicción celo por actividad acelerómetro
- [ ] Predicción parto por comportamiento
- [ ] Detección enfermedad por anomalías de movimiento
- [ ] Análisis de uso de pasturas por zona
- [ ] Índice de condición corporal por visión (cámara)
- [ ] Integración Frigate (cámaras IP)

## v0.5 — Integraciones
- [ ] API SENASA (RENSPA, DITs)
- [ ] Integración Odoo ERP (módulo ganadero)
- [ ] Balanzas electrónicas Bluetooth
- [ ] Lectores RFID
- [ ] Estaciones meteorológicas
- [ ] Sensores de agua (bebederos, lagunas)
- [ ] Sensores de nivel de silo

## v1.0 — Producción
- [ ] Martin (vector tiles desde PostGIS)
- [ ] MapProxy (caché satélite offline)
- [ ] TileServer GL completo
- [ ] Multi-establecimiento UI mejorada
- [ ] App móvil React Native (campo sin internet)
- [ ] Sync offline/online para app móvil
- [ ] Backups automáticos
- [ ] Monitoreo con Prometheus + Grafana
- [ ] CI/CD con GitHub Actions
- [ ] Kubernetes Helm chart

## Integraciones Futuras Planificadas
- INIA Balcarce (datos climáticos)
- BCRA (liquidaciones)
- Municipios (control bromatológico)
- Organismos sanitarios (certificados)
- Cooperativas (liquidaciones, remitos)
- Frigoríficos (trazabilidad carne)
