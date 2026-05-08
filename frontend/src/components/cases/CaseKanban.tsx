"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { cases as casesApi, type Case } from "@/lib/api";
import { getStatusLabel, formatCurrency } from "@/lib/case-utils";

interface KanbanColumn {
  key: string;
  label: string;
  color: string;
  statuses: string[];
}

const COLUMNS: KanbanColumn[] = [
  {
    key: "leads",
    label: "Лиды",
    color: "border-t-neutral",
    statuses: ["lead", "qualification"],
  },
  {
    key: "consultation",
    label: "Консультация",
    color: "border-t-info",
    statuses: ["consultation", "contract_signing"],
  },
  {
    key: "preparation",
    label: "Подготовка",
    color: "border-t-warning",
    statuses: ["document_collection", "document_review", "application_preparation"],
  },
  {
    key: "court",
    label: "В суде",
    color: "border-t-primary",
    statuses: ["application_filed", "court_accepted", "hearing_scheduled", "procedure_started"],
  },
  {
    key: "process",
    label: "Процедура",
    color: "border-t-danger",
    statuses: ["creditors_registry", "creditors_meeting", "asset_realization", "restructuring"],
  },
  {
    key: "completed",
    label: "Завершено",
    color: "border-t-success",
    statuses: ["fu_report", "completion", "debt_discharged"],
  },
];

export default function CaseKanban() {
  const [allCases, setAllCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    casesApi
      .list({ page: 1 })
      .then(setAllCases)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  function getCasesForColumn(col: KanbanColumn): Case[] {
    return allCases.filter((c) => col.statuses.includes(c.status));
  }

  if (loading) {
    return <div className="text-text-muted text-sm py-8">Загрузка канбан-доски...</div>;
  }

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {COLUMNS.map((col) => {
        const columnCases = getCasesForColumn(col);
        return (
          <div
            key={col.key}
            className={`flex-shrink-0 w-64 bg-surface rounded-xl border-t-4 ${col.color}`}
          >
            {/* Column Header */}
            <div className="px-4 py-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-text-body">{col.label}</h3>
              <span className="text-xs bg-surface-muted text-text-muted px-2 py-0.5 rounded-full">
                {columnCases.length}
              </span>
            </div>

            {/* Cards */}
            <div className="px-2 pb-2 space-y-2 min-h-[200px]">
              {columnCases.length === 0 ? (
                <p className="text-xs text-text-muted text-center py-8">Нет дел</p>
              ) : (
                columnCases.map((c) => (
                  <Link
                    key={c.id}
                    href={`/cases/${c.id}`}
                    className="block bg-white p-3 rounded-lg border border-neutral hover:border-border hover:shadow-sm transition-all"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-medium text-primary">
                        {c.case_number || c.id.slice(0, 8)}
                      </span>
                      {c.ai_risk_level && (
                        <span
                          className={`w-2 h-2 rounded-full ${
                            c.ai_risk_level === "high"
                              ? "bg-danger"
                              : c.ai_risk_level === "medium"
                              ? "bg-warning"
                              : "bg-success"
                          }`}
                          title={`Риск: ${c.ai_risk_level}`}
                        />
                      )}
                    </div>
                    <p className="text-xs text-text-muted mb-1">
                      {getStatusLabel(c.status)}
                    </p>
                    {c.total_debt && (
                      <p className="text-sm font-medium text-text-body">
                        {formatCurrency(c.total_debt)}
                      </p>
                    )}
                    {c.ai_score != null && (
                      <div className="mt-2 flex items-center gap-1.5">
                        <div className="flex-1 h-1.5 bg-surface-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary rounded-full"
                            style={{ width: `${c.ai_score}%` }}
                          />
                        </div>
                        <span className="text-[10px] text-text-muted">{c.ai_score}%</span>
                      </div>
                    )}
                  </Link>
                ))
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
