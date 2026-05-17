'use client'
import { Lead, FunnelStage } from '@/lib/leadgen-api'
import KanbanColumn from './KanbanColumn'

interface Props {
  stages: { key: FunnelStage; label: string }[]
  grouped: Record<FunnelStage, Lead[]>
  onUpdate: () => void
}

export default function KanbanBoard({ stages, grouped, onUpdate }: Props) {
  return (
    <div className="flex-1 flex gap-4 p-4 overflow-x-auto" style={{ backgroundColor: '#F8F7F4' }}>
      {stages.map(stage => (
        <KanbanColumn
          key={stage.key}
          stageKey={stage.key}
          label={stage.label}
          leads={grouped[stage.key] || []}
          onUpdate={onUpdate}
        />
      ))}
    </div>
  )
}
