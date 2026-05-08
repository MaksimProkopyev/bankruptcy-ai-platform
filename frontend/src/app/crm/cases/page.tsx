"use client";



import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { cases as casesApi, type Case } from "@/lib/api";
import { getStatusLabel, getStatusColor, formatCurrency, formatDate } from "@/lib/case-utils";
import CaseKanban from "@/components/cases/CaseKanban";

const STATUS_FILTERS = [
  { value: "", label: "Все" },
  { value: "lead", label: "Лиды" },
  { value: "document_collection", label: "Сбор документов" },
  { value: "application_filed", label: "Подано в суд" },
  { value: "procedure_started", label: "В процедуре" },
  { value: "debt_discharged", label: "Завершённые" },
];

function CasesPageContent() {
  const searchParams = useSearchParams();
  const [casesList, setCasesList] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState(searchParams.get("status") || "");
  const [viewMode, setViewMode] = useState<"table" | "kanban">("table");

  useEffect(() => {
    setLoading(true);
    casesApi.list({ status: statusFilter || undefined })
      .then(setCasesList)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [statusFilter]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-text">Дела</h1>
          <p className="text-sm text-text-muted mt-1">{casesList.length} дел</p>
        </div>
        <div className="flex gap-3">
          <div className="flex bg-surface-muted rounded-lg p-0.5">
            <button onClick={() => setViewMode("table")} className={`px-3 py-1.5 text-xs rounded-md ${viewMode === "table" ? "bg-white shadow-sm text-text" : "text-text-muted"}`}>Таблица</button>
            <button onClick={() => setViewMode("kanban")} className={`px-3 py-1.5 text-xs rounded-md ${viewMode === "kanban" ? "bg-white shadow-sm text-text" : "text-text-muted"}`}>Канбан</button>
          </div>
          <Link href="/crm/cases/new" className="px-4 py-2 text-sm bg-accent text-text-on-dark rounded-lg hover:bg-accent-hover">+ Новое дело</Link>
        </div>
      </div>

      {viewMode === "kanban" ? (
        <CaseKanban />
      ) : (
        <>
          <div className="flex gap-2 mb-6">
            {STATUS_FILTERS.map((f) => (
              <button key={f.value} onClick={() => setStatusFilter(f.value)}
                className={`px-3 py-1.5 text-sm rounded-lg border ${statusFilter === f.value ? "bg-primary-light border-primary text-primary-dark font-medium" : "bg-white border-neutral text-text-muted hover:bg-surface"}`}>
                {f.label}
              </button>
            ))}
          </div>

          <div className="bg-white rounded-xl border border-neutral shadow-card overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-neutral bg-primary text-text-on-dark">
                  <th className="text-left px-4 py-3 text-xs font-medium text-text-on-dark-muted uppercase">Номер</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-text-on-dark-muted uppercase">Статус</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-text-on-dark-muted uppercase">Долг</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-text-on-dark-muted uppercase">AI</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-text-on-dark-muted uppercase">Создано</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={5} className="text-center py-12 text-text-muted">Загрузка...</td></tr>
                ) : casesList.length === 0 ? (
                  <tr><td colSpan={5} className="text-center py-12 text-text-muted">Нет дел</td></tr>
                ) : (
                  casesList.map((c, index) => (
                    <tr key={c.id} className={`border-b border-neutral ${index % 2 === 0 ? 'bg-surface-muted' : ''} hover:bg-surface`}>
                      <td className="px-4 py-3"><Link href={`/cases/${c.id}`} className="text-sm font-medium text-primary hover:underline">{c.case_number || c.id.slice(0, 8)}</Link></td>
                      <td className="px-4 py-3"><span className={`inline-block px-2.5 py-1 text-xs font-medium rounded-full ${getStatusColor(c.status)}`}>{getStatusLabel(c.status)}</span></td>
                      <td className="px-4 py-3 text-sm text-text-body">{formatCurrency(c.total_debt)}</td>
                      <td className="px-4 py-3 text-sm text-text-body">{c.ai_score != null ? `${c.ai_score}%` : "—"}</td>
                      <td className="px-4 py-3 text-sm text-text-muted">{formatDate(c.created_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

import { Suspense } from "react";
export default function CasesPage() {
  return <Suspense><CasesPageContent /></Suspense>;
}
