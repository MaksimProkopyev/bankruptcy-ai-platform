"use client";

import { useState, useEffect } from "react";
import { getStats, Stats } from "@/lib/api";

const STUB_STATS: Stats = {
  total_leads: 124,
  qualified: 38,
  converted: 17,
  avg_score: 71,
  by_channel: [
    { channel: "telegram", count: 52, conversion: 18.2 },
    { channel: "website", count: 31, conversion: 12.9 },
    { channel: "vk", count: 24, conversion: 8.3 },
    { channel: "phone", count: 17, conversion: 23.5 },
  ],
};

const CHANNEL_LABELS: Record<string, string> = {
  telegram: "Telegram",
  vk: "ВКонтакте",
  website: "Сайт",
  phone: "Телефон",
  email: "Email",
};

export default function StatsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [usingStub, setUsingStub] = useState(false);

  useEffect(() => {
    getStats()
      .then(data => { setStats(data); setLoading(false); })
      .catch(() => { setStats(STUB_STATS); setUsingStub(true); setLoading(false); });
  }, []);

  if (loading) return <div className="p-8 text-center text-text-muted">Загрузка...</div>;
  if (!stats) return null;

  const conversionRate = stats.total_leads > 0 ? ((stats.converted / stats.total_leads) * 100).toFixed(1) : "0";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-primary font-heading">Статистика</h1>
          <p className="text-sm text-text-muted mt-1">Аналитика лидогенерации</p>
        </div>
        {usingStub && (
          <div className="text-xs px-3 py-1 bg-warning/10 border border-warning text-warning rounded-lg">
            API недоступен — показаны тестовые данные
          </div>
        )}
      </div>

      {/* KPI карточки */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Всего лидов", value: stats.total_leads, sub: "за всё время" },
          { label: "Квалифицировано", value: stats.qualified, sub: `${stats.total_leads > 0 ? ((stats.qualified / stats.total_leads) * 100).toFixed(0) : 0}% от всех` },
          { label: "Конвертировано", value: stats.converted, sub: `${conversionRate}% конверсия` },
          { label: "Средний score", value: stats.avg_score, sub: "по всем лидам" },
        ].map(card => (
          <div key={card.label} className="bg-white rounded-xl border border-neutral p-5 shadow-card">
            <p className="text-xs text-text-muted font-medium uppercase tracking-wide">{card.label}</p>
            <p className="text-3xl font-bold text-primary mt-1">{card.value}</p>
            <p className="text-xs text-text-muted mt-1">{card.sub}</p>
          </div>
        ))}
      </div>

      {/* Таблица по каналам */}
      <div className="bg-white rounded-xl border border-neutral shadow-card overflow-hidden">
        <div className="px-5 py-4 border-b border-neutral">
          <h2 className="font-semibold text-text">Лиды по каналам</h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neutral bg-surface">
              <th className="px-5 py-3 text-left font-medium text-text-muted">Канал</th>
              <th className="px-5 py-3 text-right font-medium text-text-muted">Кол-во</th>
              <th className="px-5 py-3 text-right font-medium text-text-muted">Конверсия %</th>
            </tr>
          </thead>
          <tbody>
            {stats.by_channel.map(row => (
              <tr key={row.channel} className="border-b border-neutral last:border-0 hover:bg-surface/50">
                <td className="px-5 py-3 font-medium">{CHANNEL_LABELS[row.channel] || row.channel}</td>
                <td className="px-5 py-3 text-right">{row.count}</td>
                <td className="px-5 py-3 text-right">
                  <span className={`font-semibold ${
                    row.conversion >= 20 ? "text-success" :
                    row.conversion >= 10 ? "text-warning" :
                    "text-danger"
                  }`}>
                    {row.conversion.toFixed(1)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
