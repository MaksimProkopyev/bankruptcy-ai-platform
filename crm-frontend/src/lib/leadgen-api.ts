const LEADGEN_URL = process.env.NEXT_PUBLIC_LEADGEN_URL || 'https://leadgen.nssb-maximum.ru'

export type LeadStatus = 'new' | 'in_progress' | 'qualified' | 'disqualified' | 'converted' | 'spam'
export type FunnelStage = 'incoming' | 'contacted' | 'qualifying' | 'hot' | 'ready_to_convert'
export type Channel = 'web' | 'telegram' | 'whatsapp' | 'vk' | 'email' | 'ok' | 'facebook' | 'avito' | 'callback' | 'max'

export interface Lead {
  id: string
  channel: Channel
  status: LeadStatus
  funnel_stage: FunnelStage
  debt_amount: number | null
  debt_type: string | null
  qualification_score: number | null
  disqualify_reason: string | null
  assigned_to: string | null
  created_at: string
  updated_at: string
  source?: {
    name: string | null
    phone: string | null
    email: string | null
  }
}

export interface LeadMessage {
  id: string
  lead_id: string
  direction: 'inbound' | 'outbound'
  channel: Channel
  content: string
  content_type: string
  sent_at: string
}

export interface Prospect {
  id: string
  lead_id: string
  qualification_data: Record<string, any>
  status: 'pending' | 'confirmed' | 'rejected' | 'converted'
  created_at: string
  lead?: Lead
}

export interface Stats {
  total_leads: number
  by_channel: Record<string, number>
  by_status: Record<string, number>
  conversion_rate: number
  avg_qualification_hours: number | null
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${LEADGEN_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!res.ok) throw new Error(`Leadgen API error: ${res.status}`)
  return res.json()
}

export const leadgenApi = {
  // Leads
  getLeads: (params?: { channel?: string; status?: string; funnel_stage?: string }) => {
    const q = new URLSearchParams(params as any).toString()
    return apiFetch<{ leads: Lead[]; total: number }>(`/api/v1/leads${q ? '?' + q : ''}`)
  },
  getLead: (id: string) => apiFetch<Lead>(`/api/v1/leads/${id}`),
  updateLead: (id: string, data: Partial<Pick<Lead, 'status' | 'funnel_stage' | 'assigned_to'>>) =>
    apiFetch<Lead>(`/api/v1/leads/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  spamLead: (id: string) =>
    apiFetch<void>(`/api/v1/leads/${id}`, { method: 'DELETE' }),
  getMessages: (id: string) =>
    apiFetch<{ messages: LeadMessage[] }>(`/api/v1/leads/${id}/messages`),
  sendMessage: (id: string, content: string) =>
    apiFetch<LeadMessage>(`/api/v1/leads/${id}/messages`, {
      method: 'POST', body: JSON.stringify({ content }),
    }),
  qualify: (id: string) =>
    apiFetch<void>(`/api/v1/leads/${id}/qualify`, { method: 'POST' }),

  // Prospects
  getProspects: () => apiFetch<{ prospects: Prospect[] }>('/api/v1/prospects'),
  confirmProspect: (id: string) =>
    apiFetch<void>(`/api/v1/prospects/${id}/confirm`, { method: 'POST' }),
  rejectProspect: (id: string) =>
    apiFetch<void>(`/api/v1/prospects/${id}/reject`, { method: 'POST' }),

  // Stats
  getStats: () => apiFetch<Stats>('/api/v1/stats'),
}
