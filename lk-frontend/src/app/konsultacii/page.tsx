"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
function getCookie(n: string) { if (typeof document === "undefined") return ""; const m = document.cookie.match(new RegExp("(^| )" + n + "=([^;]+)")); return m ? decodeURIComponent(m[2]) : ""; }
function hdr() { return { Authorization: `Bearer ${getCookie("client_token")}`, "Content-Type": "application/json" }; }

interface Con { id: string; scheduled_at: string; duration_minutes: number; type: string; status: string; topic: string | null; meeting_url: string | null; lawyer_notes: string | null; }
const TYPE_L: Record<string, string> = { phone: "Телефон", video: "Видео", office: "Офис" };
const STATUS_S: Record<string, { l: string; c: string }> = { scheduled: { l: "Запланирована", c: "bg-blue-100 text-blue-700" }, confirmed: { l: "Подтверждена", c: "bg-green-100 text-green-700" }, completed: { l: "Проведена", c: "bg-gray-100 text-gray-600" }, cancelled: { l: "Отменена", c: "bg-red-100 text-red-600" } };

export default function LkConsultationsPage() {
  const router = useRouter();
  const [upcoming, setUpcoming] = useState<Con[]>([]);
  const [past, setPast] = useState<Con[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ date: "", time: "10:00", type: "phone", topic: "" });
  const [saving, setSaving] = useState(false);
  const [lawyer, setLawyer] = useState<{ name: string; phone: string } | null>(null);

  useEffect(() => {
    const token = getCookie("client_token");
    if (!token) { router.push("/login"); return; }
    Promise.all([
      fetch(`${API}/cabinet/consultations`, { headers: hdr() }).then(r => r.json()),
      fetch(`${API}/cabinet/lawyer`, { headers: hdr() }).then(r => r.json()),
    ]).then(([c, l]) => { setUpcoming(c.upcoming || []); setPast(c.past || []); if (l.assigned) setLawyer({ name: l.name, phone: l.phone }); })
      .catch(() => router.push("/login")).finally(() => setLoading(false));
  }, [router]);

  async function book() {
    if (!form.date) return;
    setSaving(true);
    try {
      await fetch(`${API}/cabinet/consultations/book`, { method: "POST", headers: hdr(), body: JSON.stringify({ scheduled_at: new Date(`${form.date}T${form.time}:00`).toISOString(), consultation_type: form.type, topic: form.topic || null }) });
      setShowForm(false);
      const c = await fetch(`${API}/cabinet/consultations`, { headers: hdr() }).then(r => r.json());
      setUpcoming(c.upcoming || []);
    } finally { setSaving(false); }
  }

  async function cancel(id: string) { await fetch(`${API}/cabinet/consultations/${id}/cancel`, { method: "POST", headers: hdr() }); setUpcoming(p => p.filter(c => c.id !== id)); }

  if (loading) return <div className="py-12 text-center text-text-muted">Загрузка...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-text">Консультации</h1>
        <button onClick={() => setShowForm(true)} className="px-4 py-2 bg-accent text-text-on-dark text-sm rounded-xl hover:bg-accent-hover">+ Записаться</button>
      </div>

      {lawyer && (
        <div className="bg-white rounded-2xl border border-neutral p-5 mb-6 flex items-center gap-4">
          <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center text-primary font-bold text-lg">{lawyer.name.charAt(0)}</div>
          <div><p className="text-sm font-medium text-text">{lawyer.name}</p><p className="text-xs text-text-muted">Ваш юрист</p></div>
          <a href={`tel:${lawyer.phone}`} className="ml-auto px-4 py-2 bg-success/10 text-success text-sm rounded-xl hover:bg-success/20">Позвонить</a>
        </div>
      )}

      {showForm && (
        <div className="bg-primary/10 rounded-2xl p-6 mb-6">
          <h2 className="text-sm font-semibold text-primary-dark mb-4">Запись на консультацию</h2>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div><label className="block text-xs text-text-muted mb-1">Дата</label><input type="date" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} min={new Date().toISOString().split("T")[0]} className="w-full px-3 py-2 border border-neutral rounded-xl text-sm" /></div>
            <div><label className="block text-xs text-text-muted mb-1">Время</label><select value={form.time} onChange={e => setForm({ ...form, time: e.target.value })} className="w-full px-3 py-2 border border-neutral rounded-xl text-sm">{["09:00","10:00","11:00","12:00","14:00","15:00","16:00","17:00","18:00"].map(t => <option key={t}>{t}</option>)}</select></div>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div><label className="block text-xs text-text-muted mb-1">Формат</label><select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })} className="w-full px-3 py-2 border border-neutral rounded-xl text-sm"><option value="phone">Телефон</option><option value="video">Видео</option><option value="office">Офис</option></select></div>
            <div><label className="block text-xs text-text-muted mb-1">Тема</label><input type="text" value={form.topic} onChange={e => setForm({ ...form, topic: e.target.value })} placeholder="О чём поговорим?" className="w-full px-3 py-2 border border-neutral rounded-xl text-sm" /></div>
          </div>
          <div className="flex gap-3">
            <button onClick={book} disabled={saving || !form.date} className="px-5 py-2 bg-accent text-text-on-dark text-sm rounded-xl disabled:opacity-50">{saving ? "..." : "Записаться"}</button>
            <button onClick={() => setShowForm(false)} className="text-sm text-text-muted">Отмена</button>
          </div>
        </div>
      )}

      {upcoming.length > 0 && (<div className="mb-8"><h2 className="text-sm font-semibold text-text-muted uppercase mb-3">Предстоящие</h2><div className="space-y-3">{upcoming.map(c => (
        <div key={c.id} className="bg-white rounded-2xl border border-primary/20 p-5 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-text">{new Date(c.scheduled_at).toLocaleDateString("ru-RU", { weekday: "short", day: "numeric", month: "long" })} в {new Date(c.scheduled_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}</p>
            <p className="text-xs text-text-muted mt-1">{TYPE_L[c.type] || c.type} · {c.duration_minutes} мин{c.topic ? ` · ${c.topic}` : ""}</p>
          </div>
          <div className="flex gap-2">{c.meeting_url && <a href={c.meeting_url} className="px-3 py-1.5 bg-accent text-text-on-dark text-xs rounded-lg">Подключиться</a>}<button onClick={() => cancel(c.id)} className="text-xs text-danger">Отменить</button></div>
        </div>
      ))}</div></div>)}

      {past.length > 0 && (<div><h2 className="text-sm font-semibold text-gray-500 uppercase mb-3">Прошедшие</h2><div className="space-y-3">{past.map(c => (
        <div key={c.id} className="bg-white rounded-2xl border border-gray-200 p-5">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-700">{new Date(c.scheduled_at).toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" })}</p>
            <span className={`px-2 py-1 text-xs rounded-full ${STATUS_S[c.status]?.c || ""}`}>{STATUS_S[c.status]?.l || c.status}</span>
          </div>
          {c.lawyer_notes && <div className="mt-3 p-3 bg-gray-50 rounded-xl"><p className="text-xs text-gray-500 font-medium mb-1">Заметки юриста:</p><p className="text-sm text-gray-700">{c.lawyer_notes}</p></div>}
        </div>
      ))}</div></div>)}

      {upcoming.length === 0 && past.length === 0 && <div className="bg-white rounded-2xl border border-gray-200 p-8 text-center text-gray-400">Нет консультаций</div>}
    </div>
  );
}
