export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  tenant_id: string | null
}

export type UserRole = 'superadmin' | 'tenant_admin' | 'vet' | 'manager' | 'operator' | 'readonly'

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface Animal {
  id: string
  tenant_id: string
  establishment_id: string
  paddock_id: string | null
  herd_id: string | null
  ear_tag: string
  rfid: string | null
  name: string | null
  breed: string | null
  sex: 'male' | 'female'
  category: string | null
  status: AnimalStatus
  birth_date: string | null
  color: string | null
  weight_kg: number | null
  notes: string | null
  created_at: string
  updated_at: string
  paddock_name: string | null
  herd_name: string | null
  has_device: boolean
  device_uid: string | null
  last_lat: number | null
  last_lon: number | null
}

export type AnimalStatus = 'active' | 'sold' | 'dead' | 'sick' | 'quarantine' | 'transferred'

export interface AnimalListResponse {
  items: Animal[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface Paddock {
  id: string
  tenant_id: string
  establishment_id: string
  name: string
  code: string | null
  color: string | null
  area_ha: number | null
  max_capacity: number | null
  current_load: number
  status: PaddockStatus
  polygon: GeoJSONPolygon | null
  pasture_type: string | null
  notes: string | null
  created_at: string
  animal_count: number
  device_count: number
}

export type PaddockStatus = 'occupied' | 'empty' | 'resting' | 'maintenance'

export interface GeoJSONPolygon {
  type: 'Polygon'
  coordinates: number[][][]
}

export interface Device {
  id: string
  tenant_id: string
  establishment_id: string
  animal_id: string | null
  device_uid: string
  device_type: DeviceType
  name: string | null
  firmware: string | null
  battery_pct: number | null
  rssi: number | null
  temperature: number | null
  activity_score: number | null
  is_online: boolean
  last_seen: string | null
  last_lat: number | null
  last_lon: number | null
  is_active: boolean
  created_at: string
  animal_ear_tag: string | null
}

export type DeviceType = 'gps_collar' | 'gps_tag' | 'sensor' | 'gateway'

export interface Alert {
  id: string
  tenant_id: string
  establishment_id: string | null
  animal_id: string | null
  device_id: string | null
  alert_type: AlertType
  severity: AlertSeverity
  status: AlertStatus
  title: string
  message: string | null
  created_at: string
  resolved_at: string | null
  animal_ear_tag: string | null
  device_uid: string | null
}

export type AlertType =
  | 'outside_geofence' | 'immobile' | 'low_battery' | 'device_offline'
  | 'abnormal_activity' | 'possible_heat' | 'possible_birth'
  | 'vaccine_due' | 'temperature_high' | 'manual'

export type AlertSeverity = 'info' | 'warning' | 'critical'
export type AlertStatus = 'open' | 'acknowledged' | 'resolved'

export interface Establishment {
  id: string
  tenant_id: string
  name: string
  code: string | null
  color: string | null
  province: string | null
  municipality: string | null
  total_area_ha: number | null
  lat: number | null
  lon: number | null
  boundary: GeoJSONPolygon | null
  is_active: boolean
  paddock_count: number
  animal_count: number
  device_count: number
}

export interface DashboardKPIs {
  total_animals: number
  monitored_animals: number
  total_paddocks: number
  paddocks_occupied: number
  open_alerts: number
  critical_alerts: number
  offline_devices: number
  low_battery_devices: number
  possible_heat: number
  possible_birth: number
}

export interface MapAnimal {
  device_id: string
  device_uid: string
  animal_id: string | null
  name?: string | null
  field_id?: string | null
  field_name?: string | null
  paddock_id?: string | null
  paddock_name?: string | null
  outside_field?: boolean
  gateway_id?: string | null
  lat: number
  lon: number
  battery_pct: number | null
  temperature?: number | null
  is_online: boolean
  online: number
  last_seen: string | null
  device_type: string
  gps_fresh?: number | null
  a0x?: number | null
  a0y?: number | null
  a0z?: number | null
  a1x?: number | null
  a1y?: number | null
  a1z?: number | null
  movement?: 'moving' | 'still' | 'unknown'
}

export interface TemperatureHistoryPoint {
  ts: string
  temperature: number
}

export interface TemperatureHistoryResponse {
  dev_addr: string
  points: TemperatureHistoryPoint[]
}

export interface BatteryHistoryPoint {
  ts: string
  battery: number
}

export interface BatteryHistoryResponse {
  dev_addr: string
  points: BatteryHistoryPoint[]
}

export interface AccelHistoryPoint {
  ts: string
  a0x?: number
  a0y?: number
  a0z?: number
  a1x?: number
  a1y?: number
  a1z?: number
}

export interface AccelHistoryResponse {
  dev_addr: string
  points: AccelHistoryPoint[]
}

export interface ConsumptionCycle {
  ts: string
  battery: number | null
  charging: number | null
  wake_boots: number | null
  wake_time_ms: number | null
  duty_pct: number
  cycle_mah: number
}

export interface ConsumptionResponse {
  dev_addr: string
  samples: number
  avg_cycle_mah: number
  daily_mah: number
  autonomy_days: number | null
  brownouts_detected: number
  last_charging: number | null
  cycles: ConsumptionCycle[]
}

export interface MapData {
  animals: MapAnimal[]
  gateways: MapGateway[]
  paddocks: { type: string; features: GeoJSONFeature[] }
  alerts: Alert[]
}

export interface MapGateway {
  gateway_id: string
  name: string | null
  lat: number
  lon: number
  online: number
  battery_pct?: number | null
  charging?: number | null
  temperature?: number | null
  humidity?: number | null
  last_seen?: string | null
  device_count?: number
}

export interface GeoJSONFeature {
  type: 'Feature'
  properties: Record<string, unknown>
  geometry: { type: string; coordinates: unknown }
}

export interface LoraPacket {
  id: number
  gateway_id: string
  gateway_name: string | null
  received_at: number | null
  rssi: number | null
  snr: number | null
  freq_mhz: number | null
  sf: number | null
  payload_hex: string | null
  dev_addr: string | null
  device_name: string | null
  temperature: number | null
  humidity: number | null
  battery: number | null
  mtype_str: string | null
  fcnt: number | null
  created_at: string
}

export interface LoraPacketResponse {
  count: number
  limit: number
  offset: number
  packets: LoraPacket[]
}

export interface LoraStats {
  total_packets: number
  unique_gateways: number
  unique_devices: number
  gateways_registered: number
  devices_registered: number
  last_packet: LoraPacket | null
}

export interface LoraConfig {
  listen_port: string
  auth_password: string
  max_packets: string
}

export interface LoraGateway {
  id: number
  gateway_id: string
  name: string | null
  lat: number | null
  lon: number | null
  wifi_ssid: string | null
  wifi_rssi: number | null
  wifi_ip: string | null
  battery_pct: number | null
  charging: number | null
  temperature: number | null
  humidity: number | null
  uptime_s: number | null
  pkts_total: number | null
  location: string | null
  last_seen: string | null
  updated_at: string | null
  is_active: number
  is_paired: number
  pairing_code: string | null
  pairing_expires_at: string | null
  notes: string | null
  total_packets: number | null
  online: number
  device_count: number
}

export interface LoraPendingGateway {
  gateway_id: string
  pairing_expires_at: string | null
  last_seen: string | null
  updated_at: string | null
  lat: number | null
  lon: number | null
  wifi_ssid: string | null
  wifi_rssi: number | null
  battery_pct: number | null
  uptime_s: number | null
  pkts_total: number | null
  is_paired: number
}

export interface LoraPendingDevice {
  dev_addr: string
  name: string | null
  device_type: string | null
  pairing_code: string
  pairing_expires_at: string | null
  battery_pct: number | null
  last_seen: string | null
}

export interface LoraDevice {
  id: number
  dev_addr: string
  name: string | null
  dev_eui: string | null
  device_type: string
  gateway_id: string | null
  refresh_freq_s: number | null
  hw_version: string | null
  lat: number | null
  lon: number | null
  wifi_ssid: string | null
  wifi_rssi: number | null
  battery_pct: number | null
  temperature: number | null
  humidity: number | null
  gps_fresh: number | null
  a0x: number | null
  a0y: number | null
  a0z: number | null
  a1x: number | null
  a1y: number | null
  a1z: number | null
  last_seen: string | null
  updated_at: string | null
  is_active: number
  notes: string | null
  total_packets: number | null
  online: number
}

export interface WaterPoint {
  id: string
  name: string
  type: 'water' | 'trough'
  lat: number
  lon: number
  radius_m: number
  capacity_l: number | null
  notes: string | null
  is_active: boolean
  establishment_id: string
}

export interface ZoneVisit {
  id: string
  water_point_id: string | null
  water_point_name: string | null
  paddock_id: string | null
  paddock_name: string | null
  event_type: 'paddock_enter' | 'paddock_exit' | 'water_visit'
  dev_addr: string
  duration_s: number | null
  entered_at: string
  exited_at: string | null
}
