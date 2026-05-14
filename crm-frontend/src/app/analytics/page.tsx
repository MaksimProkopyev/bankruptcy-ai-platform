"use client";

import { useEffect, useState } from "react";
import { analytics, type FunnelRow, type LawyerWorkload, type DashboardSummary } from "@/lib/api";
import { formatCurrency } from "@/lib/case-utils";

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [funnel, setFunnel] = useState<FunnelRow[]>([]);
  const [workload, setWorkload] = useState<LawyerWorkload[]>([]);

  useEffect(() => {
    analytics.summary().then(setSummary).catch(console.error);
    analytics.funnel().then(setFunnel).catch(console.error);
    analytics.lawyerWorkload().then(setWorkload).catch(console.error);
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Аналитика</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <p className="text-sm text-gray-500">Всего дел</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{summary?.total_cases ?? "—"}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <p className="text-sm text-gray-500">Активные дела</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{summary?.active_cases ?? "—"}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <p className="text-sm text-gray-500">Выручка</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{summary ? formatCurrency(summary.total_revenue) : "—"}</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Воронка конверсий</h2>
        {funnel.length === 0 ? (
          <p className="text-sm text-gray-400">Нет данных</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="text-left px-3 py-2 text-xs font-medium text-gray-500">Месяц</th>
                  <th className="text-right px-3 py-2 text-xs font-medium text-gray-500">Лиды</th>
                  <th className="text-right px-3 py-2 text-xs font-medium text-gray-500">Квалиф.</th>
                  <th className="text-right px-3 py-2 text-xs font-medium text-gray-500">Конс.</th>
                  <th className="text-right px-3 py-2 text-xs font-medium text-gray-500">Договоры</th>
                  <th className="text-right px-3 py-2 text-xs font-medium text-gray-500">Подано</th>
                  <th className="text-right px-3 py-2 text-xs font-medium text-gray-500">Завершено</th>
                </tr>
              </thead>
              <tbody>
                {funnel.map((row, i) => (
                  <tr key={i} className="border-b border-gray-50">
                    <td className="px-3 py-2 text-sm text-gray-900">{row.month}</td>
                    <td className="px-3 py-2 text-sm text-right">{row.total_leads}</td>
                    <td className="px-3 py-2 text-sm text-right">{row.qualified}</td>
                    <td className="px-3 py-2 text-sm text-right">{row.consultations}</td>
                    <td className="px-3 py-2 text-sm text-right font-medium">{row.contracts}</td>
                    <td className="px-3 py-2 text-sm text-right">{row.filed}</td>
                    <td className="px-3 py-2 text-sm text-right text-green-600 font-medium">{row.completed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Загрузка юристов</h2>
        {workload.length === 0 ? (
          <p className="text-sm text-gray-400">Нет данных</p>
        ) : (
          <div className="space-y-4">
            {workload.map((w) => (
              <div key={w.lawyer_id} className="flex items-center gap-4">
                <div className="w-40 text-sm font-medium text-gray-900 truncate">{w.lawyer_name}</div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary rounded-full"
                        style={{ width: `${Math.min((w.active_court_cases / 25) * 100, 100)}%` }}
                      />
                    </div>
                    <span className="text-sm text-gray-600 w-16 text-right">{w.total_cases} дел</span>
                  </div>
                </div>
                <div className="text-xs text-gray-400 w-20 text-right">
                  {w.completed_cases} заверш.
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
