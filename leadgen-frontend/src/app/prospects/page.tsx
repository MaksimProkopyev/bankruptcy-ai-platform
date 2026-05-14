"use client";

import { useState, useEffect } from "react";
import { getProspects, confirmProspect, rejectProspect, Prospect } from "@/lib/api";

const CHANNEL_LABELS: Record<string, string> = {
  telegram: "Telegram",
  vk: "ВКонтакте",
  website: "Сайт",
  phone: "Телефон",
  email: "Email",
};

export default function ProspectsPage() {
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState<string | null>(null);

  const load = () => {
    getProspects()
      .then(data => { setProspects(data); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  async function handleConfirm(id: string) {
    setActing(id);
    try {
      await confirmProspect(id);
      setProspects(prev => prev.filter(p => p.id !== id));
    } finally { setActing(null); }
  }

  async function handleReject(id: string) {
    setActing(id);
    try {
      await rejectProspect(id);
      setProspects(prev => prev.filter(p => p.id !== id));
    } finally { setActing(null); }
  }

  if (loading) return <div className="p-8 text-center text-text-muted">Загрузка...</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary font-heading">Подтверждение</h1>
        <p className="text-sm text-text-muted mt-1">Очередь квалифицированных лидов</p>
      </div>

      {prospects.length === 0 ? (
        <div className="bg-white rounded-xl border border-neutral p-12 text-center shadow-card">
          <p className="text-text-muted">Нет лидов, ожидающих подтверждения</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-neutral shadow-card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral bg-surface">
                <th className="px-4 py-3 text-left font-medium text-text-muted">ФИО</th>
                <th className="px-4 py-3 text-left font-medium text-text-muted">Телефон</th>
                <th className="px-4 py-3 text-left font-medium text-text-muted">Канал</th>
                <th className="px-4 py-3 text-left font-medium text-text-muted">Score</th>
                <th className="px-4 py-3 text-left font-medium text-text-muted">Квалифицирован</th>
                <th className="px-4 py-3 text-right font-medium text-text-muted">Действия</th>
              </tr>
            </thead>
            <tbody>
              {prospects.map(prospect => (
                <tr key={prospect.id} className="border-b border-neutral last:border-0 hover:bg-surface/50">
                  <td className="px-4 py-3 font-medium">{prospect.full_name || "—"}</td>
                  <td className="px-4 py-3 text-text-muted">{prospect.phone || "—"}</td>
                  <td className="px-4 py-3">{CHANNEL_LABELS[prospect.channel] || prospect.channel}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full font-bold ${
                      prospect.score >= 80 ? "bg-success/15 text-success" :
                      prospect.score >= 60 ? "bg-warning/15 text-warning" :
                      "bg-danger/15 text-danger"
                    }`}>
                      {prospect.score}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-text-muted">
                    {prospect.qualified_at ? new Date(prospect.qualified_at).toLocaleDateString("ru-RU") : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => handleConfirm(prospect.id)}
                        disabled={acting === prospect.id}
                        className="px-3 py-1.5 bg-success text-white rounded-lg text-xs font-medium hover:opacity-90 disabled:opacity-50"
                      >
                        Подтвердить
                      </button>
                      <button
                        onClick={() => handleReject(prospect.id)}
                        disabled={acting === prospect.id}
                        className="px-3 py-1.5 bg-danger text-white rounded-lg text-xs font-medium hover:opacity-90 disabled:opacity-50"
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
  );
}
