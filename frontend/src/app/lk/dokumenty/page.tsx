"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
function getCookie(n: string): string { if (typeof document === "undefined") return ""; const m = document.cookie.match(new RegExp("(^| )" + n + "=([^;]+)")); return m ? decodeURIComponent(m[2]) : ""; }

interface ChecklistItem { type: string; description: string; required: boolean; is_collected: boolean; category: string; }

export default function LkDocumentsPage() {
  const router = useRouter();
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [progress, setProgress] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getCookie("client_token");
    if (!token) { router.push("/lk/login"); return; }
    fetch(`${API_URL}/cabinet/documents`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(data => { setChecklist(data.checklist || []); setProgress(data.progress_percent || 0); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) return <div className="py-12 text-center text-gray-400">Загрузка...</div>;

  const collected = checklist.filter(d => d.is_collected);
  const missing = checklist.filter(d => !d.is_collected && d.required);

  return (
    <div>
      <h1 className="text-xl font-semibold text-text mb-6">Документы</h1>

      {/* Progress */}
      <div className="bg-white rounded-2xl border border-neutral p-6 mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-text-muted">Прогресс сбора документов</span>
          <span className="text-sm font-semibold text-primary">{progress}%</span>
        </div>
        <div className="w-full h-2 bg-surface-muted rounded-full overflow-hidden">
          <div className="h-full bg-primary rounded-full" style={{ width: `${progress}%` }} />
        </div>
        <p className="text-xs text-text-muted mt-2">Собрано {collected.length} из {checklist.length} документов</p>
      </div>

      {/* Missing (required) */}
      {missing.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-danger uppercase mb-3">Нужно загрузить ({missing.length})</h2>
          <div className="space-y-2">
            {missing.map((d) => (
              <div key={d.type} className="bg-white rounded-xl border border-danger/20 p-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-text">{d.description}</p>
                  <p className="text-xs text-text-muted mt-0.5">{d.category}</p>
                </div>
                <label className="px-4 py-2 bg-accent text-text-on-dark text-xs rounded-lg cursor-pointer hover:bg-accent-hover">
                  Загрузить
                  <input type="file" className="hidden" accept="image/*,.pdf" onChange={(e) => {/* TODO: upload */}} />
                </label>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Collected */}
      {collected.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-success uppercase mb-3">Загружено ({collected.length})</h2>
          <div className="space-y-2">
            {collected.map((d) => (
              <div key={d.type} className="bg-white rounded-xl border border-success/20 p-4 flex items-center justify-between">
                <p className="text-sm text-text">{d.description}</p>
                <span className="text-xs text-success font-medium">Готово</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
