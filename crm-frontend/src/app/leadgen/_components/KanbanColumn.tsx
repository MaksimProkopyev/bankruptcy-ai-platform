import { Lead, FunnelStage } from '@/lib/leadgen-api'
import LeadCard from './LeadCard'

interface Props {
  stageKey: FunnelStage
  label: string
  leads: Lead[]
  onUpdate: () => void
}

export default function KanbanColumn({ label, leads, onUpdate }: Props) {
  return (
    <div className="flex flex-col w-64 shrink-0">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold text-gray-600">{label}</span>
        <span className="text-xs bg-gray-200 text-gray-600 rounded-full px-2 py-0.5">
          {leads.length}
        </span>
      </div>
      <div className="flex flex-col gap-2">
        {leads.map(lead => (
          <LeadCard key={lead.id} lead={lead} onUpdate={onUpdate} />
        ))}
        {leads.length === 0 && (
          <div className="text-xs text-gray-400 text-center py-8 border-2 border-dashed border-gray-200 rounded-lg">
            Нет лидов
          </div>
        )}
      </div>
    </div>
  )
}
