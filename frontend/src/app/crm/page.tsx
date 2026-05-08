"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { analytics, type DashboardSummary } from "@/lib/api";
import { formatCurrency } from "@/lib/case-utils";

export default function CrmDashboard() {
  const [data, setData] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    analytics.summary().then(setData).catch(console.error);
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-text">Дашборд</h1>
          <p className="text-sm text-text-muted mt-1">Обзор по всем делам</p>
        </div>
        <Link href="/crm/cases/new" className="px-4 py-2 text-sm bg-accent text-text-on-dark rounded-lg hover:bg-accent-hover">
          + Новое дело
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {[
          { label: "Всего дел", value: data?.total_cases ?? "—", icon: "📁" },
          { label: "Активные", value: data?.active_cases ?? "—", icon: "⚡" },
          { label: "Выручка", value: data ? formatCurrency(data.total_revenue) : "—", icon: "💰" },
        ].map((card) => (
          <div key={card.label} className="bg-white rounded-xl border border-neutral shadow-card p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-muted">{card.label}</p>
                <p className="text-2xl font-semibold text-text mt-1">{card.value}</p>
              </div>
              <span className="text-2xl">{card.icon}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-neutral shadow-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-medium text-text">Ближайшие дедлайны</h2>
            <Link href="/crm/deadlines" className="text-xs text-primary hover:text-primary-dark">Все →</Link>
          </div>
          <p className="text-sm text-text-muted">Загрузка...</p>
        </div>
        <div className="bg-white rounded-xl border border-neutral shadow-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-medium text-text">Последние лиды</h2>
            <Link href="/crm/cases?status=lead" className="text-xs text-primary hover:text-primary-dark">Все →</Link>
          </div>
          <p className="text-sm text-text-muted">Загрузка...</p>
        </div>
      </div>
    </div>
  );
}
