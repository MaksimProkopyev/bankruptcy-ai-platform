'use client'
import { Lead, leadgenApi } from '@/lib/leadgen-api'
import Link from 'next/link'
import ChannelBadge from './ChannelBadge'

interface Props { lead: Lead; onUpdate: () => void }

export default function LeadCard({ lead, onUpdate }: Props) {
  const handleSpam = async (e: React.MouseEvent) => {
    e.preventDefault()
    if (!confirm('Пометить как спам?')) return
    await leadgenApi.spamLead(lead.id)
    onUpdate()
  }

  return (
    <Link
      href={`/leadgen/${lead.id}`}
      className="block bg-white rounded-lg p-3 shadow-sm hover:shadow-md transition-shadow border border-gray-100"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <ChannelBadge channel={lead.channel} />
        {lead.qualification_score !== null && (
          <span className="text-xs font-bold" style={{ color: '#C9A84C' }}>
            {lead.qualification_score}
          </span>
        )}
      </div>
      <div className="text-sm font-medium text-gray-800 truncate">
        {lead.source?.name || lead.source?.phone || 'Без имени'}
      </div>
      {lead.debt_amount && (
        <div className="text-xs text-gray-500 mt-1">
          {new Intl.NumberFormat('ru-RU').format(lead.debt_amount)} ₽
        </div>
      )}
      <div className="flex items-center justify-between mt-2">
        <span className="text-xs text-gray-400">
          {new Date(lead.created_at).toLocaleDateString('ru-RU')}
        </span>
        <button onClick={handleSpam} className="text-xs text-red-400 hover:text-red-600">
          Спам
        </button>
      </div>
    </Link>
  )
}
