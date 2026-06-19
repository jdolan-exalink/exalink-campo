import api from '@/lib/api'
import { db, type LocalAnimal, type SyncLog } from '@/lib/db'
import type { Animal } from '@/types'

function serverToLocal(a: Animal): LocalAnimal {
  return {
    id: a.id,
    server_id: a.id,
    ear_tag: a.ear_tag,
    rfid: a.rfid ?? undefined,
    name: a.name ?? undefined,
    breed: a.breed ?? undefined,
    sex: a.sex,
    category: a.category as LocalAnimal['category'],
    status: a.status,
    birth_date: a.birth_date ?? undefined,
    color: a.color ?? undefined,
    weight_kg: a.weight_kg ?? undefined,
    paddock_id: a.paddock_id ?? undefined,
    herd_id: a.herd_id ?? undefined,
    establishment_id: a.establishment_id,
    notes: a.notes ?? undefined,
    sync_status: 'synced',
    updated_at_local: a.updated_at,
    updated_at_server: a.updated_at,
  }
}

export interface SyncResult {
  pulled: number
  pushed: number
  errors: number
  duration_ms: number
}

export async function pullAnimals(): Promise<number> {
  let page = 1
  let pulled = 0

  while (true) {
    const { data } = await api.get(`/animals?page=${page}&page_size=200`)
    const items: Animal[] = data.items ?? []
    if (!items.length) break

    await db.transaction('rw', db.animals, async () => {
      for (const a of items) {
        const local = await db.animals.get(a.id)
        // Local pending changes win — skip overwrite
        if (local?.sync_status === 'pending') continue
        await db.animals.put(serverToLocal(a))
        pulled++
      }
    })

    if (data.page >= data.pages) break
    page++
  }

  return pulled
}

export async function pushPending(): Promise<{ pushed: number; errors: number }> {
  let pushed = 0
  let errors = 0

  // Push pending animals
  const pendingAnimals = await db.animals.where('sync_status').equals('pending').toArray()
  for (const animal of pendingAnimals) {
    try {
      const payload = {
        ear_tag: animal.ear_tag,
        rfid: animal.rfid ?? null,
        name: animal.name ?? null,
        breed: animal.breed ?? null,
        sex: animal.sex,
        category: animal.category ?? null,
        status: animal.status,
        birth_date: animal.birth_date ?? null,
        color: animal.color ?? null,
        weight_kg: animal.weight_kg ?? null,
        paddock_id: animal.paddock_id ?? null,
        herd_id: animal.herd_id ?? null,
        notes: animal.notes ?? null,
      }

      if (animal.server_id) {
        await api.put(`/animals/${animal.server_id}`, payload)
        await db.animals.update(animal.id, {
          sync_status: 'synced',
          updated_at_server: new Date().toISOString(),
        })
      } else {
        if (!animal.establishment_id) { errors++; continue }
        const { data } = await api.post('/animals', {
          ...payload,
          establishment_id: animal.establishment_id,
        })
        await db.animals.update(animal.id, {
          server_id: data.id,
          sync_status: 'synced',
          updated_at_server: data.updated_at,
        })
      }
      pushed++
    } catch (e) {
      console.error('[sync] push animal', animal.id, e)
      errors++
    }
  }

  // Push pending pesajes
  const pendingPesajes = await db.pesajes.where('sync_status').equals('pending').toArray()
  for (const p of pendingPesajes) {
    try {
      let serverId = p.server_animal_id
      if (!serverId) {
        const local = await db.animals.get(p.animal_id)
        if (!local?.server_id) continue  // wait for animal to sync first
        serverId = local.server_id
        await db.pesajes.update(p.id, { server_animal_id: serverId })
      }
      await api.post('/weights', {
        animal_id: serverId,
        weight_kg: p.peso_kg,
        measure_date: p.fecha,
        method: p.metodo ?? null,
        notes: p.observaciones ?? null,
      })
      await db.pesajes.update(p.id, { sync_status: 'synced' })
      pushed++
    } catch (e) {
      console.error('[sync] push pesaje', p.id, e)
      errors++
    }
  }

  // Push pending reproducciones
  const pendingRepros = await db.reproducciones.where('sync_status').equals('pending').toArray()
  for (const r of pendingRepros) {
    try {
      let serverId = r.server_animal_id
      if (!serverId) {
        const local = await db.animals.get(r.animal_id)
        if (!local?.server_id) continue
        serverId = local.server_id
        await db.reproducciones.update(r.id, { server_animal_id: serverId })
      }
      await api.post('/reproduction', {
        animal_id: serverId,
        event_type: r.tipo,
        event_date: r.fecha,
        notes: r.observaciones ?? null,
      })
      await db.reproducciones.update(r.id, { sync_status: 'synced' })
      pushed++
    } catch (e) {
      console.error('[sync] push repro', r.id, e)
      errors++
    }
  }

  return { pushed, errors }
}

export async function fullSync(): Promise<SyncResult> {
  const start = Date.now()
  let pulled = 0
  let errors = 0

  try {
    pulled = await pullAnimals()
  } catch (e) {
    console.error('[sync] pull failed', e)
    errors++
  }

  const { pushed, errors: pushErrors } = await pushPending()
  errors += pushErrors
  const duration_ms = Date.now() - start

  const log: Omit<SyncLog, 'id'> = {
    timestamp: new Date().toISOString(),
    direction: 'full',
    status: errors === 0 ? 'success' : pulled + pushed > 0 ? 'partial' : 'error',
    records_in: pulled,
    records_out: pushed,
    error: errors > 0 ? `${errors} error(s)` : undefined,
    duration_ms,
  }
  await db.syncLogs.add(log)

  return { pulled, pushed, errors, duration_ms }
}

export async function getLastSync(): Promise<SyncLog | undefined> {
  return db.syncLogs.orderBy('id').last()
}

export async function getPendingCount(): Promise<number> {
  const [a, p, r] = await Promise.all([
    db.animals.where('sync_status').equals('pending').count(),
    db.pesajes.where('sync_status').equals('pending').count(),
    db.reproducciones.where('sync_status').equals('pending').count(),
  ])
  return a + p + r
}
