'use client'
import { useEffect, useState } from 'react'
import { leadgenApi, Prospect } from '@/lib/leadgen-api'
import Link from 'next/link'

export default function ProspectsPage() {
  const [prospects, setProspects] = useState<Prospect[]>([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    const data = await leadgenApi.getProspects()
    setProspects(data)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const handleConfirm = async (id: string) => {
    await leadgenApi.confirmProspect(id)
    load()
  }

  const handleReject = async (id: string) => {
    await leadgenApi.rejectProspect(id)
    load()
  }

  return (
    <div className="p-6">
      <div className="flex items-center gap-4 mb-6">
        <Link href="/leadgen" className="text-sm text-gray-400 hover:text-gray-600">← Воронка</Link>
        <h1 className="font-serif text-xl font-semibold" style={{ color: '#1B3A5C' }}>
          Prospects — ожидают подтверждения
        </h1>
      </div>

      {loading ? (
        <p className="text-gray-400">Загрузка...</p>
      ) : (
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left">
                <th className="px-4 py-3 text-gray-500 font-medium">Лид</th>
                <th className="px-4 py-3 text-gray-500 font-medium">Долг</th>
                <th className="px-4 py-3 text-gray-500 font-medium">Score</th>
                <th className="px-4 py-3 text-gray-500 font-medium">Канал</th>
                <th className="px-4 py-3 text-gray-500 font-medium">Дата</th>
                <th className="px-4 py-3 text-gray-500 font-medium">Действия</th>
              </tr>
            </thead>
            <tbody>
              {prospects.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                    Нет prospects на подтверждении
                  </td>
                </tr>
              )}
              {prospects.map(p => (
                <tr key={p.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link href={`/leadgen/${p.lead_id}`} className="text-blue-600 hover:underline">
                      {p.qualification_data?.name || p.lead_id.slice(0, 8)}
                    </Link>
                    <p className="text-xs text-gray-400">{p.qualification_data?.phone}</p>
                  </td>
                  <td className="px-4 py-3">
                    {p.qualification_data?.debt_amount
                      ? `${new Intl.NumberFormat('ru-RU').format(p.qualification_data.debt_amount)} ₽`
                      : '—'}
                  </td>
                  <td className="px-4 py-3 font-bold" style={{ color: '#C9A84C' }}>
                    {p.qualification_data?.score ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {p.qualification_data?.channel ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {new Date(p.created_at).toLocaleDateString('ru-RU')}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleConfirm(p.id)}
                        className="px-3 py-1 rounded-lg text-white text-xs font-medium"
                        style={{ backgroundColor: '#1B3A5C' }}
                      >
                        Подтвердить → CRM
                      </button>
                      <button
                        onClick={() => handleReject(p.id)}
                        className="px-3 py-1 rounded-lg border border-red-200 text-red-500 text-xs"
                      >
                        Отклонить
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
