"use client";

import { useState, useEffect, useCallback } from "react";
import { Stats } from "@/types/leadgen";
import { API_BASE, formatDate } from "@/lib/leadgen-utils";
import StatsWidget from "@/components/leadgen/StatsWidget";
import ChannelBadge from "@/components/leadgen/ChannelBadge";
import { Channel } from "@/types/leadgen";

export default function StatsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/stats`);
      if (!res.ok) throw new Error();
      const data: Stats = await res.json();
      setStats(data);
    } catch {
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-48 mb-6" />
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white rounded-xl h-32 shadow-card" />
          ))}
        </div>
        <div className="bg-white rounded-xl h-64 shadow-card" />
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="text-4xl">📊</div>
        <p className="text-text-muted">Не удалось загрузить статистику</p>
        <button
          onClick={fetchStats}
          className="text-sm underline"
          style={{ color: "#C9A84C" }}
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  const maxChannelCount = Math.max(
    1,
    ...stats.by_channel.map((c) => c.count)
  );

  const funnelMax = Math.max(1, stats.funnel.all);
  const funnelRows = [
    { label: "Все лиды", value: stats.funnel.all },
    { label: "Контакт", value: stats.funnel.contacted },
    { label: "Квалификация", value: stats.funnel.qualifying },
    { label: "Готовы", value: stats.funnel.ready },
    { label: "Конвертированы", value: stats.funnel.converted },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <h1
        className="text-2xl font-bold"
        style={{ fontFamily: "Georgia, serif", color: "#1B3A5C" }}
      >
        Статистика
      </h1>

      {/* Top widgets */}
      <div className="grid grid-cols-4 gap-4">
        <StatsWidget
          label="Лидов сегодня"
          value={stats.leads_today}
          accentColor="#1B3A5C"
        />
        <StatsWidget
          label="Квалифицировано"
          value={stats.leads_qualified}
          accentColor="#C9A84C"
        />
        <StatsWidget
          label="Конвертировано"
          value={stats.leads_converted}
          accentColor="#1D9E75"
        />
        <StatsWidget
          label="Средний score"
          value={Math.round(stats.avg_score)}
          accentColor="#1B3A5C"
        />
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Bar chart: by channel */}
        <div className="bg-white rounded-xl shadow-card p-6">
          <h2
            className="text-base font-semibold mb-4"
            style={{ fontFamily: "Georgia, serif", color: "#1B3A5C" }}
          >
            Лиды по каналам
          </h2>
          {stats.by_channel.length === 0 ? (
            <p className="text-sm text-text-muted">Нет данных</p>
          ) : (
            <div className="space-y-3">
              {[...stats.by_channel]
                .sort((a, b) => b.count - a.count)
                .map((item) => {
                  const pct = (item.count / maxChannelCount) * 100;
                  return (
                    <div key={item.channel} className="flex items-center gap-3">
                      <div className="w-28 flex-shrink-0">
                        <ChannelBadge
                          channel={item.channel as Channel}
                          showLabel
                        />
                      </div>
                      <div className="flex-1 flex items-center gap-2">
                        <div
                          className="h-5 rounded-sm transition-all"
                          style={{
                            width: `${pct}%`,
                            background: "#C9A84C",
                            minWidth: "4px",
                          }}
                        />
                        <span className="text-xs font-semibold text-text-body">
                          {item.count}
                        </span>
                      </div>
                    </div>
                  );
                })}
            </div>
          )}
        </div>

        {/* Funnel */}
        <div className="bg-white rounded-xl shadow-card p-6">
          <h2
            className="text-base font-semibold mb-4"
            style={{ fontFamily: "Georgia, serif", color: "#1B3A5C" }}
          >
            Воронка конверсии
          </h2>
          <div className="space-y-2">
            {funnelRows.map((row, idx) => {
              const pct = (row.value / funnelMax) * 100;
              // Gradient from Navy to Gold
              const t = idx / (funnelRows.length - 1);
              const r = Math.round(27 + (201 - 27) * t);
              const g = Math.round(58 + (168 - 58) * t);
              const b = Math.round(92 + (76 - 92) * t);
              const color = `rgb(${r},${g},${b})`;

              return (
                <div key={row.label} className="flex items-center gap-3">
                  <div className="w-32 text-xs text-text-muted flex-shrink-0">
                    {row.label}
                  </div>
                  <div className="flex-1 flex items-center gap-2">
                    <div
                      className="h-6 rounded-sm transition-all"
                      style={{
                        width: `${Math.max(pct, 2)}%`,
                        background: color,
                      }}
                    />
                    <span className="text-xs font-semibold text-text-body">
                      {row.value}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Activity table */}
      {stats.activity && stats.activity.length > 0 && (
        <div className="bg-white rounded-xl shadow-card overflow-hidden">
          <div className="px-6 py-4 border-b border-neutral">
            <h2
              className="text-base font-semibold"
              style={{ fontFamily: "Georgia, serif", color: "#1B3A5C" }}
            >
              Активность за 7 дней
            </h2>
          </div>
          <table className="w-full text-sm">
            <thead style={{ background: "#F8F7F4" }}>
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-text-muted uppercase tracking-wide">
                  Дата
                </th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-text-muted uppercase tracking-wide">
                  Новых лидов
                </th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-text-muted uppercase tracking-wide">
                  Квалифицировано
                </th>
                <th className="px-6 py-3 text-right text-xs font-semibold text-text-muted uppercase tracking-wide">
                  Конвертировано
                </th>
              </tr>
            </thead>
            <tbody>
              {stats.activity.map((row, idx) => (
                <tr
                  key={row.date}
                  className={idx % 2 === 0 ? "bg-white" : "bg-surface-muted"}
                >
                  <td className="px-6 py-3 text-text-body">
                    {formatDate(row.date)}
                  </td>
                  <td className="px-6 py-3 text-right font-medium text-text">
                    {row.new_leads}
                  </td>
                  <td className="px-6 py-3 text-right font-medium text-text">
                    {row.qualified}
                  </td>
                  <td className="px-6 py-3 text-right font-medium text-text">
                    {row.converted}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
