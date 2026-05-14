"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
function getCookie(n: string) { if (typeof document === "undefined") return ""; const m = document.cookie.match(new RegExp("(^| )" + n + "=([^;]+)")); return m ? decodeURIComponent(m[2]) : ""; }

interface CalEvent { type: string; title: string; date: string; icon: string; priority?: string; location?: string; duration_minutes?: number; meeting_url?: string; }

export default function LkCalendarPage() {
  const router = useRouter();
  const [events, setEvents] = useState<CalEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getCookie("client_token");
    if (!token) { router.push("/login"); return; }
    fetch(`${API}/cabinet/calendar`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => setEvents(Array.isArray(d) ? d : []))
      .catch(() => router.push("/login"))
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) return <div className="py-12 text-center text-text-muted">Загрузка...</div>;

  const now = new Date();

  // Group events by month
  const grouped: Record<string, CalEvent[]> = {};
  events.forEach(e => {
    const d = new Date(e.date);
    const key = d.toLocaleDateString("ru-RU", { month: "long", year: "numeric" });
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(e);
  });

  const TYPE_STYLES: Record<string, string> = {
    hearing: "border-l-purple-500 bg-purple-50",
    deadline: "border-l-orange-500 bg-orange-50",
    consultation: "border-l-blue-500 bg-blue-50",
    payment: "border-l-green-500 bg-green-50",
  };

  return (
    <div>
      <h1 className="text-xl font-semibold text-text mb-6">Календарь событий</h1>

      {events.length === 0 ? (
        <div className="bg-white rounded-2xl border border-neutral p-8 text-center text-text-muted">
          Нет предстоящих событий
        </div>
      ) : (
        <div className="space-y-8">
          {Object.entries(grouped).map(([month, items]) => (
            <div key={month}>
              <h2 className="text-sm font-semibold text-text-muted uppercase mb-3">{month}</h2>
              <div className="space-y-2">
                {items.map((e, i) => {
                  const d = new Date(e.date);
                  const isPast = d < now;
                  const daysLeft = Math.ceil((d.getTime() - now.getTime()) / 86400000);

                  return (
                    <div key={i} className={`border-l-4 rounded-xl p-4 ${TYPE_STYLES[e.type] || "border-l-gray-300 bg-white"} ${isPast ? "opacity-60" : ""}`}>
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <span className="text-lg">{e.icon}</span>
                          <div>
                            <p className="text-sm font-medium text-text">{e.title}</p>
                            <p className="text-xs text-text-muted mt-0.5">
                              {d.toLocaleDateString("ru-RU", { weekday: "short", day: "numeric", month: "long" })}
                              {e.duration_minutes ? ` · ${e.duration_minutes} мин` : ""}
                              {e.location ? ` · ${e.location}` : ""}
                            </p>
                          </div>
                        </div>
                        <div className="text-right flex-shrink-0 ml-4">
                          {isPast ? (
                            <span className="text-xs text-text-muted">Прошло</span>
                          ) : daysLeft === 0 ? (
                            <span className="text-xs font-medium text-red-600">Сегодня</span>
                          ) : daysLeft === 1 ? (
                            <span className="text-xs font-medium text-orange-600">Завтра</span>
                          ) : (
                            <span className="text-xs text-text-muted">{daysLeft} дн.</span>
                          )}
                          {e.meeting_url && !isPast && (
                            <a href={e.meeting_url} target="_blank" className="block mt-1 text-xs text-primary hover:underline">
                              Подключиться
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-6 text-xs text-text-muted flex items-center gap-4">
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-purple-200" /> Заседания</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-orange-200" /> Дедлайны</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-blue-200" /> Консультации</span>
      </div>
    </div>
  );
}
