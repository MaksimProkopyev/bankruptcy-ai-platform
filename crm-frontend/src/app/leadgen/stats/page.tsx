'use client'
import { useEffect, useState } from 'react'
import { leadgenApi, Stats } from '@/lib/leadgen-api'
import Link from 'next/link'

export default function StatsPage() {
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    leadgenApi.getStats().then(setStats)
  }, [])

  if (!stats) return <div className="p-8 text-gray-400">Загрузка...</div>

  return (
    <div className="p-6">
      <div className="flex items-center gap-4 mb-6">
        <Link href="/leadgen" className="text-sm text-gray-400 hover:text-gray-600">← Воронка</Link>
        <h1 className="font-serif text-xl font-semibold" style={{ color: '#1B3A5C' }}>
          Статистика лидогенерации
        </h1>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Всего лидов', value: stats.total_leads },
          { label: 'Конверсия', value: `${(stats.conversion_rate * 100).toFixed(1)}%` },
          {
            label: 'Среднее время квалификации',
            value: stats.avg_qualification_hours
              ? `${stats.avg_qualification_hours.toFixed(1)}ч`
              : '—',
          },
          { label: 'Каналов активно', value: Object.keys(stats.by_channel).length },
        ].map(card => (
          <div key={card.label} className="bg-white rounded-xl p-5 shadow-sm">
            <p className="text-xs text-gray-500 mb-1">{card.label}</p>
            <p className="text-2xl font-bold" style={{ color: '#1B3A5C' }}>{card.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-5 shadow-sm">
          <h3 className="font-semibold text-gray-700 mb-4">По каналам</h3>
          {Object.entries(stats.by_channel).map(([ch, cnt]) => (
            <div key={ch} className="flex items-center justify-between py-2 border-b last:border-0">
              <span className="text-sm text-gray-600 capitalize">{ch}</span>
              <span className="font-semibold text-sm" style={{ color: '#1B3A5C' }}>{cnt}</span>
            </div>
          ))}
        </div>
        <div className="bg-white rounded-xl p-5 shadow-sm">
          <h3 className="font-semibold text-gray-700 mb-4">По статусам</h3>
          {Object.entries(stats.by_status).map(([st, cnt]) => (
            <div key={st} className="flex items-center justify-between py-2 border-b last:border-0">
              <span className="text-sm text-gray-600">{st}</span>
              <span className="font-semibold text-sm" style={{ color: '#1B3A5C' }}>{cnt}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
