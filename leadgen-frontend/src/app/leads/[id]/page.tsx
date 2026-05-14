"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { getLead, qualifyLead, markSpam, Lead } from "@/lib/api";
import UnifiedInbox from "@/components/leads/UnifiedInbox";

const CHANNEL_LABELS: Record<string, string> = {
  telegram: "Telegram",
  vk: "ВКонтакте",
  website: "Сайт",
  phone: "Телефон",
  email: "Email",
};

const STAGE_LABELS: Record<string, string> = {
  incoming: "Входящий",
  contacted: "Контакт установлен",
  qualifying: "Квалификация",
  hot: "Горячий",
  ready_to_convert: "Готов к переводу",
};

export default function LeadDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [lead, setLead] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);

  useEffect(() => {
    getLead(id)
      .then(data => { setLead(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [id]);

  async function handleQualify() {
    if (!lead) return;
    setActing(true);
    try {
      await qualifyLead(lead.id);
      setLead(prev => prev ? { ...prev, status: "qualified" } : prev);
    } finally { setActing(false); }
  }

  async function handleSpam() {
    if (!lead) return;
    setActing(true);
    try {
      await markSpam(lead.id);
      router.push("/leads");
    } finally { setActing(false); }
  }

  if (loading) return <div className="p-8 text-center text-text-muted">Загрузка...</div>;
  if (!lead) return <div className="p-8 text-center text-text-muted">Лид не найден</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button onClick={() => router.push("/leads")} className="text-text-muted hover:text-primary text-sm">← Назад</button>
        <h1 className="text-2xl font-bold text-primary font-heading">{lead.full_name || "Без имени"}</h1>
      </div>

      <div className="flex gap-6 h-[calc(100vh-180px)]">
        {/* Левая панель — данные лида */}
        <div className="w-80 shrink-0 space-y-4">
          <div className="bg-white rounded-xl border border-neutral p-5 shadow-card space-y-3">
            <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wide">Данные лида</h2>

            <div>
              <p className="text-xs text-text-muted">Телефон</p>
              <p className="font-medium">{lead.phone || "—"}</p>
            </div>
            <div>
              <p className="text-xs text-text-muted">Канал</p>
              <p className="font-medium">{CHANNEL_LABELS[lead.channel] || lead.channel}</p>
            </div>
            <div>
              <p className="text-xs text-text-muted">Этап воронки</p>
              <p className="font-medium">{STAGE_LABELS[lead.funnel_stage] || lead.funnel_stage}</p>
            </div>
            <div>
              <p className="text-xs text-text-muted">Score</p>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-sm font-bold ${
                lead.score >= 80 ? "bg-success/15 text-success" :
                lead.score >= 60 ? "bg-warning/15 text-warning" :
                "bg-danger/15 text-danger"
              }`}>
                {lead.score}
              </span>
            </div>
            <div>
              <p className="text-xs text-text-muted">Статус</p>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs border border-border">
                {lead.status}
              </span>
            </div>
            <div>
              <p className="text-xs text-text-muted">Создан</p>
              <p className="font-medium text-sm">{new Date(lead.created_at).toLocaleDateString("ru-RU")}</p>
            </div>
          </div>

          {/* Кнопки действий */}
          <div className="space-y-2">
            <button
              onClick={handleQualify}
              disabled={acting || lead.status === "qualified"}
              className="w-full py-2.5 bg-primary text-text-on-dark rounded-lg text-sm font-medium hover:bg-primary-dark disabled:opacity-50"
            >
              Квалифицировать
            </button>
            {lead.status === "qualified" && (
              <button
                className="w-full py-2.5 bg-accent text-text-on-dark rounded-lg text-sm font-medium hover:bg-accent-hover"
              >
                В CRM
              </button>
            )}
            <button
              onClick={handleSpam}
              disabled={acting}
              className="w-full py-2.5 border border-danger text-danger rounded-lg text-sm font-medium hover:bg-danger/10 disabled:opacity-50"
            >
              Спам
            </button>
          </div>
        </div>

        {/* Правая панель — unified inbox */}
        <div className="flex-1">
          <UnifiedInbox leadId={id} />
        </div>
      </div>
    </div>
  );
}
