const LEADGEN_API = process.env.NEXT_PUBLIC_LEADGEN_API_URL || 'http://localhost:8002'
const CRM_API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface Lead {
  id: string
  full_name: string | null
  phone: string | null
  channel: string
  score: number
  funnel_stage: string
  status: string
  created_at: string
}

export interface Message {
  id: string
  lead_id: string
  direction: 'inbound' | 'outbound'
  text: string
  channel: string
  created_at: string
}

export interface Prospect {
  id: string
  full_name: string | null
  phone: string | null
  channel: string
  score: number
  qualified_at: string | null
}

export interface Stats {
  total_leads: number
  qualified: number
  converted: number
  avg_score: number
  by_channel: { channel: string; count: number; conversion: number }[]
}

function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('token')
}

async function request<T>(url: string, init: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...init.headers,
  }
  const res = await fetch(url, { ...init, headers })
  if (res.status === 401) {
    document.cookie = 'staff_token=; path=/; max-age=0'
    localStorage.removeItem('token')
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getLeads(): Promise<Lead[]> {
  return request<Lead[]>(`${LEADGEN_API}/api/v1/leads`)
}

export async function getLead(id: string): Promise<Lead> {
  return request<Lead>(`${LEADGEN_API}/api/v1/leads/${id}`)
}

export async function getMessages(leadId: string): Promise<Message[]> {
  return request<Message[]>(`${LEADGEN_API}/api/v1/leads/${leadId}/messages`)
}

export async function sendMessage(leadId: string, text: string): Promise<Message> {
  return request<Message>(`${LEADGEN_API}/api/v1/leads/${leadId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ text }),
  })
}

export async function qualifyLead(id: string): Promise<Lead> {
  return request<Lead>(`${LEADGEN_API}/api/v1/leads/${id}/qualify`, { method: 'POST' })
}

export async function markSpam(id: string): Promise<void> {
  return request<void>(`${LEADGEN_API}/api/v1/leads/${id}/spam`, { method: 'POST' })
}

export async function getProspects(): Promise<Prospect[]> {
  return request<Prospect[]>(`${LEADGEN_API}/api/v1/prospects`)
}

export async function confirmProspect(id: string): Promise<void> {
  return request<void>(`${LEADGEN_API}/api/v1/prospects/${id}/confirm`, { method: 'POST' })
}

export async function rejectProspect(id: string): Promise<void> {
  return request<void>(`${LEADGEN_API}/api/v1/prospects/${id}/reject`, { method: 'POST' })
}

export async function getStats(): Promise<Stats> {
  return request<Stats>(`${LEADGEN_API}/api/v1/stats`)
}

export { CRM_API }
