import Dexie, { type Table } from 'dexie'

export type SyncStatus = 'synced' | 'pending' | 'conflict'

export type AnimalCategory = 'ternero' | 'ternera' | 'novillo' | 'vaquillona' | 'toro' | 'vaca' | 'buey'
export type AnimalStatus = 'active' | 'sold' | 'dead' | 'sick' | 'quarantine' | 'transferred'
export type ReproTipo = 'heat' | 'service' | 'insemination' | 'pregnancy_check' | 'birth' | 'abortion' | 'drying'

export interface LocalAnimal {
  id: string                   // UUID (server ID when synced, local crypto.randomUUID() when new)
  server_id?: string           // server UUID — undefined until first successful push
  ear_tag: string              // caravana visual
  rfid?: string                // caravana electrónica ISO 11784/11785
  name?: string
  breed?: string
  sex: 'male' | 'female'
  category?: AnimalCategory
  status: AnimalStatus
  birth_date?: string          // YYYY-MM-DD
  color?: string
  weight_kg?: number
  paddock_id?: string
  herd_id?: string
  establishment_id?: string
  notes?: string
  sync_status: SyncStatus
  updated_at_local: string     // ISO timestamp — conflict resolution key
  updated_at_server?: string
}

export interface LocalPesaje {
  id: string
  animal_id: string            // LocalAnimal.id
  server_animal_id?: string    // resolved server UUID on push
  peso_kg: number
  fecha: string                // YYYY-MM-DD
  metodo?: string
  observaciones?: string
  sync_status: SyncStatus
  created_at: string
}

export interface LocalRepro {
  id: string
  animal_id: string
  server_animal_id?: string
  tipo: ReproTipo
  fecha: string
  observaciones?: string
  sync_status: SyncStatus
  created_at: string
}

export interface SyncLog {
  id?: number
  timestamp: string
  direction: 'pull' | 'push' | 'full'
  status: 'success' | 'error' | 'partial'
  records_in: number
  records_out: number
  error?: string
  duration_ms: number
}

class CampoDB extends Dexie {
  animals!: Table<LocalAnimal>
  pesajes!: Table<LocalPesaje>
  reproducciones!: Table<LocalRepro>
  syncLogs!: Table<SyncLog>

  constructor() {
    super('exalink_campo_v1')
    this.version(1).stores({
      animals:        'id, server_id, ear_tag, rfid, sync_status, category, status',
      pesajes:        'id, animal_id, fecha, sync_status',
      reproducciones: 'id, animal_id, fecha, sync_status',
      syncLogs:       '++id, timestamp, direction, status',
    })
  }
}

export const db = new CampoDB()
