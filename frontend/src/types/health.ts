export interface HealthEvent {
  id: string
  animal_id: string
  establishment_id: string
  event_type: 'vaccine' | 'treatment' | 'disease' | 'surgery' | 'checkup' | 'deworming' | 'vitamin'
  product_name: string
  dose: string | null
  route: string | null
  event_date: string
  next_date: string | null
  vet_name: string | null
  cost: number | null
  notes: string | null
  created_at: string
}
