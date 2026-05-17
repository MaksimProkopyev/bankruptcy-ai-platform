'use client'
import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { leadgenApi, Lead, LeadMessage, FunnelStage } from '@/lib/leadgen-api'
import ChannelBadge from '../_components/ChannelBadge'
import MessageThread from '../_components/MessageThread'
import MessageInput from '../_components/MessageInput'

const STAGE_OPTIONS: { value: FunnelStage; label: string }[] = [
  { value: 'incoming', label: 'Входящий' },
  { value: 'contacted', label: 'Контакт' },
  { value: 'qualifying', label: 'Квалификация' },
  { value: 'hot', label: 'Горячий' },
  { value: 'ready_to_convert', label: 'Готов к конвертации' },
]

export default function LeadDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [lead, setLead] = useState<Lead | null>(null)
  const [messages, setMessages] = useState<LeadMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [qualifying, setQualifying] = useState(false)

  const load = async () => {
    const [l, m] = await Promise.all([
      leadgenApi.getLead(id),
      leadgenApi.getMessages(id),
    ])
    setLead(l)
    setMessages(m)
    setLoading(false)
  }

  useEffect(() => { load() }, [id])

  const handleStageChange = async (stage: FunnelStage) => {
    await leadgenApi.updateLead(id, { funnel_stage: stage })
    setLead(prev => prev ? { ...prev, funnel_stage: stage } : prev)
  }

  const handleQualify = async () => {
    setQualifying(true)
    try {
      await leadgenApi.qualify(id)
      alert('Задача квалификации отправлена в AI Studio')
    } finally {
      setQualifying(false)
    }
  }

  const handleSpam = async () => {
    if (!confirm('Пометить как спам и убрать из воронки?')) return
    await leadgenApi.spamLead(id)
    router.push('/leadgen')
  }

  const handleSend = async (content: string) => {
    const msg = await leadgenApi.sendMessage(id, content)
    setMessages(prev => [...prev, msg])
  }

  if (loading) return <div className="p-8 text-gray-400">Загрузка...</div>
  if (!lead) return <div className="p-8 text-red-400">Лид не найден</div>

  return (
    <div className="flex h-full">
      {/* Left panel — info */}
      <div className="w-80 shrink-0 border-r bg-white p-6 flex flex-col gap-6">
        <div>
          <button
            onClick={() => router.push('/leadgen')}
            className="text-sm text-gray-400 hover:text-gray-600 mb-4"
          >
            ← Воронка
          </button>
          <div className="flex items-center gap-2 mb-1">
            <ChannelBadge channel={lead.channel} />
            {lead.qualification_score !== null && (
              <span className="text-sm font-bold" style={{ color: '#C9A84C' }}>
                Score: {lead.qualification_score}
              </span>
            )}
          </div>
          <h2 className="font-serif text-lg font-semibold mt-2" style={{ color: '#1B3A5C' }}>
            {lead.source?.name || 'Без имени'}
          </h2>
          {lead.source?.phone && <p className="text-sm text-gray-600">{lead.source.phone}</p>}
          {lead.source?.email && <p className="text-sm text-gray-500">{lead.source.email}</p>}
        </div>

        {lead.debt_amount && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500">Сумма долга</p>
            <p className="text-base font-semibold" style={{ color: '#1B3A5C' }}>
              {new Intl.NumberFormat('ru-RU').format(lead.debt_amount)} ₽
            </p>
            {lead.debt_type && <p className="text-xs text-gray-500 mt-1">{lead.debt_type}</p>}
          </div>
        )}

        <div>
          <label className="text-xs text-gray-500 block mb-1">Этап воронки</label>
          <select
            value={lead.funnel_stage}
            onChange={e => handleStageChange(e.target.value as FunnelStage)}
            className="w-full border rounded-lg px-3 py-2 text-sm"
          >
            {STAGE_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-2 mt-auto">
          <button
            onClick={handleQualify}
            disabled={qualifying}
            className="w-full py-2 rounded-lg text-sm text-white font-medium disabled:opacity-50"
            style={{ backgroundColor: '#1B3A5C' }}
          >
            {qualifying ? 'Отправка...' : 'AI Квалификация'}
          </button>
          <button
            onClick={handleSpam}
            className="w-full py-2 rounded-lg text-sm border border-red-200 text-red-500 hover:bg-red-50"
          >
            Спам
          </button>
        </div>
      </div>

      {/* Right panel — messages */}
      <div className="flex-1 flex flex-col">
        <div className="px-6 py-3 border-b bg-white">
          <span className="text-sm text-gray-500">Unified inbox — {messages.length} сообщений</span>
        </div>
        <MessageThread messages={messages} />
        <MessageInput onSend={handleSend} />
      </div>
    </div>
  )
}
