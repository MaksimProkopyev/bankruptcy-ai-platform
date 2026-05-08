"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { cases as casesApi, type CaseDetail } from "@/lib/api";
import { getStatusLabel, getStatusColor, formatCurrency, formatDate, RISK_COLORS } from "@/lib/case-utils";

type Tab = "overview" | "creditors" | "documents" | "timeline" | "deadlines";

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) casesApi.get(id).then(setCaseData).catch(console.error).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <p className="text-gray-400">Загрузка дела...</p>;
  if (!caseData) return <p className="text-red-500">Дело не найдено</p>;

  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: "overview", label: "Обзор" },
    { key: "creditors", label: "Кредиторы", count: caseData.creditors.length },
    { key: "documents", label: "Документы", count: caseData.documents.length },
    { key: "timeline", label: "Таймлайн" },
    { key: "deadlines", label: "Сроки", count: caseData.deadlines.length },
  ];

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <Link href="/crm/cases" className="text-sm text-gray-400 hover:text-gray-600 mb-2 block">← Все дела</Link>
          <h1 className="text-2xl font-semibold text-gray-900">{caseData.case_number || `Дело ${caseData.id.slice(0, 8)}`}</h1>
          <div className="flex items-center gap-3 mt-2">
            <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${getStatusColor(caseData.status)}`}>{getStatusLabel(caseData.status)}</span>
            {caseData.ai_risk_level && <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${RISK_COLORS[caseData.ai_risk_level] || ""}`}>Риск: {caseData.ai_risk_level}</span>}
          </div>
        </div>
      </div>

      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm border-b-2 transition-colors ${tab === t.key ? "border-brand-600 text-brand-700 font-medium" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
            {t.label}{t.count != null && <span className="ml-1.5 text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded-full">{t.count}</span>}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-medium text-gray-500 uppercase mb-4">Клиент</h3>
            {caseData.client ? (
              <div className="space-y-2">
                <p className="text-lg font-medium text-gray-900">{caseData.client.last_name} {caseData.client.first_name}</p>
                <p className="text-sm text-gray-600">{caseData.client.phone}</p>
                {caseData.client.email && <p className="text-sm text-gray-600">{caseData.client.email}</p>}
              </div>
            ) : <p className="text-sm text-gray-400">Нет данных</p>}
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-medium text-gray-500 uppercase mb-4">Финансы</h3>
            <div className="space-y-3">
              <div className="flex justify-between"><span className="text-sm text-gray-500">Долг</span><span className="text-sm font-medium">{formatCurrency(caseData.total_debt)}</span></div>
              <div className="flex justify-between"><span className="text-sm text-gray-500">Стоимость</span><span className="text-sm font-medium">{formatCurrency(caseData.service_fee)}</span></div>
              {caseData.ai_score != null && <div className="flex justify-between"><span className="text-sm text-gray-500">AI-скоринг</span><span className="text-sm font-medium">{caseData.ai_score}%</span></div>}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-medium text-gray-500 uppercase mb-4">Суд</h3>
            {caseData.case_number ? (
              <div className="space-y-2">
                <p className="text-sm font-medium">{caseData.case_number}</p>
                {caseData.court_name && <p className="text-sm text-gray-600">{caseData.court_name}</p>}
                {caseData.filing_date && <div className="flex justify-between"><span className="text-sm text-gray-500">Подано</span><span className="text-sm">{formatDate(caseData.filing_date)}</span></div>}
              </div>
            ) : <p className="text-sm text-gray-400">Заявление не подано</p>}
          </div>
        </div>
      )}

      {tab === "creditors" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead><tr className="border-b border-gray-100 bg-gray-50/50">
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Кредитор</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Тип</th>
              <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">Сумма</th>
              <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase">Реестр</th>
            </tr></thead>
            <tbody>
              {caseData.creditors.length === 0 ? <tr><td colSpan={4} className="text-center py-8 text-gray-400">Нет кредиторов</td></tr> :
              caseData.creditors.map((cr) => (
                <tr key={cr.id} className="border-b border-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{cr.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{cr.creditor_type}</td>
                  <td className="px-4 py-3 text-sm text-right font-medium">{formatCurrency(cr.total_amount)}</td>
                  <td className="px-4 py-3 text-center">{cr.included_in_registry ? "✓" : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "documents" && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          {caseData.documents.length === 0 ? <p className="text-sm text-gray-400">Нет документов</p> :
            <div className="space-y-3">
              {caseData.documents.map((d) => (
                <div key={d.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div><p className="text-sm font-medium text-gray-900">{d.file_name || d.document_type}</p><p className="text-xs text-gray-400">{d.document_type} · {formatDate(d.created_at)}</p></div>
                  <span className={`px-2 py-1 text-xs rounded-full ${d.status === "validated" ? "bg-green-100 text-green-700" : d.status === "processing" ? "bg-yellow-100 text-yellow-700" : "bg-gray-100 text-gray-600"}`}>{d.status}</span>
                </div>
              ))}
            </div>
          }
        </div>
      )}

      {tab === "timeline" && <div className="bg-white rounded-xl border border-gray-200 p-6"><p className="text-sm text-gray-400">Таймлайн событий</p></div>}

      {tab === "deadlines" && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          {caseData.deadlines.length === 0 ? <p className="text-sm text-gray-400">Нет сроков</p> :
            <div className="space-y-3">
              {caseData.deadlines.map((d) => (
                <div key={d.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div><p className="text-sm font-medium text-gray-900">{d.title}</p><p className="text-xs text-gray-400">{formatDate(d.due_date)}</p></div>
                  <span className={`px-2 py-1 text-xs rounded-full ${d.priority === "critical" ? "bg-red-100 text-red-700" : d.priority === "high" ? "bg-orange-100 text-orange-700" : "bg-gray-100 text-gray-600"}`}>{d.priority}</span>
                </div>
              ))}
            </div>
          }
        </div>
      )}
    </div>
  );
}
