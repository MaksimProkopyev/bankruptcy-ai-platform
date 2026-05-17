'use client'
import { useEffect, useState } from 'react'
import { leadgenApi, Lead, FunnelStage } from '@/lib/leadgen-api'
import KanbanBoard from './_components/KanbanBoard'
import Link from 'next/link'

const STAGES: { key: FunnelStage; label: string }[] = [
  { key: 'incoming', label: 'Входящие' },
  { key: 'contacted', label: 'Контакт' },
  { key: 'qualifying', label: 'Квалификация' },
  { key: 'hot', label: 'Горячие' },
  { key: 'ready_to_convert', label: 'К конвертации' },
]

export default function LeadgenPage() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const data = await leadgenApi.getLeads()
      setLeads(data.items)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const grouped = STAGES.reduce((acc, s) => {
    acc[s.key] = leads.filter(l => l.funnel_stage === s.key)
    return acc
  }, {} as Record<FunnelStage, Lead[]>)

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-4 border-b bg-white">
        <h1 className="font-serif text-xl font-semibold" style={{ color: '#1B3A5C' }}>
          Воронка лидов
        </h1>
        <div className="flex gap-3">
          <Link
            href="/leadgen/prospects"
            className="px-4 py-2 text-sm rounded-lg border border-gray-200 hover:bg-gray-50"
          >
            Prospects ({leads.filter(l => l.status === 'qualified').length})
          </Link>
          <Link
            href="/leadgen/stats"
            className="px-4 py-2 text-sm rounded-lg border border-gray-200 hover:bg-gray-50"
          >
            Статистика
          </Link>
          <button
            onClick={load}
            className="px-4 py-2 text-sm rounded-lg text-white"
            style={{ backgroundColor: '#1B3A5C' }}
          >
            Обновить
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center text-gray-400">Загрузка...</div>
      ) : (
        <KanbanBoard stages={STAGES} grouped={grouped} onUpdate={load} />
      )}
    </div>
  )
}
