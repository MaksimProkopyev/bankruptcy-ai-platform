"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function getCookie(n: string) {
  if (typeof document === "undefined") return "";
  const m = document.cookie.match(new RegExp("(^| )" + n + "=([^;]+)"));
  return m ? decodeURIComponent(m[2]) : "";
}

interface StageInfo {
  label: string;
  description: string;
  what_now: string;
  what_next: string | null;
  client_action: string | null;
}

interface CompletedStage {
  key: string;
  label: string;
}

interface CaseData {
  has_case: boolean;
  case_number?: string;
  status?: string;
  progress_percent?: number;
  stage?: StageInfo;
  completed_stages?: CompletedStage[];
  current_stage_index?: number;
  total_stages?: number;
  total_debt?: number;
  creditors_count?: number;
  court_name?: string;
  court_case_number?: string;
  next_hearing?: string;
  upcoming_deadlines?: { title: string; due_date: string; priority: string }[];
  documents_progress?: number;
  documents_missing?: number;
  lawyer?: { name: string; phone?: string } | null;
  financial_manager?: string | null;
}

interface EventItem { title: string; description?: string; date: string; }

export default function LkMainPage() {
  const router = useRouter();
  const [caseData, setCaseData] = useState<CaseData | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getCookie("client_token");
    if (!token) { router.push("/lk/login"); return; }
    const h = { Authorization: `Bearer ${token}` };
    Promise.all([
      fetch(`${API}/cabinet/case`, { headers: h }).then(r => r.json()),
      fetch(`${API}/cabinet/events`, { headers: h }).then(r => r.json()),
    ])
      .then(([c, e]) => { setCaseData(c); setEvents(e); })
      .catch(() => router.push("/lk/login"))
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) return <div className="py-12 text-center text-gray-400">Загрузка...</div>;

  if (!caseData?.has_case) {
    return (
      <div className="bg-white rounded-2xl border border-neutral p-10 text-center">
        <h2 className="text-xl font-semibold text-gray-900">Добро пожаловать!</h2>
        <p className="text-text-muted mt-2">У вас пока нет активного дела.</p>
        <a href="/" className="inline-block mt-6 px-6 py-2.5 bg-accent text-text-on-dark rounded-xl text-sm font-medium hover:bg-accent-hover">
          Пройти бесплатную оценку
        </a>
      </div>
    );
  }

  const stage = caseData.stage;
  const pct = caseData.progress_percent || 0;

  return (
    <div>
      {/* Current stage card */}
      <div className="bg-white rounded-2xl border border-neutral p-6 mb-6">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs text-text-muted">Дело {caseData.case_number}</p>
          <span className="text-sm font-semibold text-primary">{pct}%</span>
        </div>
        <h1 className="text-xl font-semibold text-gray-900">{stage?.label}</h1>

        {/* Progress bar */}
        <div className="w-full h-2.5 bg-surface-muted rounded-full overflow-hidden mt-4">
          <div className="h-full bg-primary rounded-full transition-all duration-700" style={{ width: `${pct}%` }} />
        </div>

        {/* Stage description */}
        <p className="text-sm text-text-body mt-4">{stage?.description}</p>

        {/* What's happening / what's next */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <div className="bg-surface-muted rounded-xl p-4">
            <p className="text-xs font-medium text-text-muted uppercase mb-1">Что происходит сейчас</p>
            <p className="text-sm text-text-body">{stage?.what_now}</p>
          </div>
          {stage?.what_next && (
            <div className="bg-primary-light rounded-xl p-4">
              <p className="text-xs font-medium text-primary uppercase mb-1">Следующий шаг</p>
              <p className="text-sm text-primary-dark">{stage?.what_next}</p>
            </div>
          )}
        </div>

        {/* Client action required */}
        {stage?.client_action && (
          <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-xl p-4">
            <p className="text-xs font-medium text-yellow-700 uppercase mb-1">Требуется от вас</p>
            <p className="text-sm text-yellow-800">{stage.client_action}</p>
          </div>
        )}
      </div>

      {/* Progress stages — mini dots */}
      {caseData.completed_stages && caseData.completed_stages.length > 0 && (
        <div className="bg-white rounded-2xl border border-neutral p-5 mb-6">
          <p className="text-xs font-medium text-text-muted uppercase mb-3">Пройденные этапы</p>
          <div className="flex flex-wrap gap-2">
            {caseData.completed_stages.map((s) => (
              <span key={s.key} className="text-xs bg-green-50 text-green-700 px-2.5 py-1 rounded-full">
                ✓ {s.label}
              </span>
            ))}
            <span className="text-xs bg-primary-light text-primary-dark px-2.5 py-1 rounded-full font-medium">
              ● {stage?.label}
            </span>
          </div>
        </div>
      )}

      {/* Quick info cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-2xl border border-neutral p-4">
          <p className="text-xs text-text-muted">Долг</p>
          <p className="text-base font-semibold text-gray-900 mt-1">
            {caseData.total_debt ? `${caseData.total_debt.toLocaleString("ru-RU")} ₽` : "—"}
          </p>
        </div>
        <div className="bg-white rounded-2xl border border-neutral p-4">
          <p className="text-xs text-text-muted">Кредиторов</p>
          <p className="text-base font-semibold text-gray-900 mt-1">{caseData.creditors_count || 0}</p>
        </div>
        <div className="bg-white rounded-2xl border border-neutral p-4">
          <p className="text-xs text-text-muted">Документы</p>
          <p className="text-base font-semibold text-gray-900 mt-1">
            {caseData.documents_progress != null ? `${caseData.documents_progress}%` : "—"}
          </p>
          {(caseData.documents_missing || 0) > 0 && (
            <Link href="/lk/dokumenty" className="text-xs text-primary mt-1 block">не хватает {caseData.documents_missing}</Link>
          )}
        </div>
        <div className="bg-white rounded-2xl border border-neutral p-4">
          <p className="text-xs text-text-muted">Юрист</p>
          <p className="text-base font-semibold text-gray-900 mt-1">
            {caseData.lawyer ? caseData.lawyer.name.split(" ")[0] : "—"}
          </p>
          {caseData.lawyer && <Link href="/lk/yurist" className="text-xs text-primary mt-1 block">подробнее</Link>}
        </div>
      </div>

      {/* Upcoming deadlines */}
      {caseData.upcoming_deadlines && caseData.upcoming_deadlines.length > 0 && (
        <div className="bg-white rounded-2xl border border-neutral p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 uppercase mb-3">Ближайшие события</h2>
          {caseData.upcoming_deadlines.map((d, i) => (
            <div key={i} className="flex items-center justify-between py-2.5 border-b border-surface-muted last:border-0">
              <span className="text-sm text-gray-900">{d.title}</span>
              <span className="text-xs text-text-muted">{new Date(d.due_date).toLocaleDateString("ru-RU")}</span>
            </div>
          ))}
        </div>
      )}

      {/* Quick actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Link href="/lk/dokumenty" className="bg-white rounded-xl border border-neutral p-4 text-center hover:bg-surface-muted transition-colors">
          <span className="text-xl">📄</span>
          <p className="text-xs text-text-body mt-2">Документы</p>
        </Link>
        <Link href="/lk/kreditory" className="bg-white rounded-xl border border-neutral p-4 text-center hover:bg-surface-muted transition-colors">
          <span className="text-xl">🏦</span>
          <p className="text-xs text-text-body mt-2">Кредиторы</p>
        </Link>
        <Link href="/lk/chat" className="bg-white rounded-xl border border-neutral p-4 text-center hover:bg-surface-muted transition-colors">
          <span className="text-xl">💬</span>
          <p className="text-xs text-text-body mt-2">AI-ассистент</p>
        </Link>
        <Link href="/lk/yurist" className="bg-white rounded-xl border border-neutral p-4 text-center hover:bg-surface-muted transition-colors">
          <span className="text-xl">📅</span>
          <p className="text-xs text-text-body mt-2">Консультация</p>
        </Link>
      </div>

      {/* Timeline */}
      <div className="bg-white rounded-2xl border border-neutral p-6">
        <h2 className="text-sm font-semibold text-gray-700 uppercase mb-4">История событий</h2>
        {events.length === 0 ? <p className="text-sm text-text-muted">Пока нет событий</p> : (
          <div className="space-y-4">
            {events.slice(0, 10).map((e, i) => (
              <div key={i} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className="w-2 h-2 bg-primary rounded-full mt-2" />
                  {i < Math.min(events.length, 10) - 1 && <div className="w-px flex-1 bg-border mt-1" />}
                </div>
                <div className="pb-3">
                  <p className="text-sm text-gray-900">{e.title}</p>
                  {e.description && <p className="text-xs text-text-muted mt-0.5">{e.description}</p>}
                  <p className="text-xs text-text-muted mt-1">
                    {new Date(e.date).toLocaleDateString("ru-RU", { day: "numeric", month: "long" })}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
