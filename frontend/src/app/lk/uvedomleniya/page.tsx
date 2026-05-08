"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
function getCookie(n: string) { if (typeof document === "undefined") return ""; const m = document.cookie.match(new RegExp("(^| )" + n + "=([^;]+)")); return m ? decodeURIComponent(m[2]) : ""; }
function hdr() { return { Authorization: `Bearer ${getCookie("client_token")}`, "Content-Type": "application/json" }; }

interface Notif { id: string; title: string; body: string | null; is_read: boolean; date: string; }

export default function LkNotificationsPage() {
  const router = useRouter();
  const [notifications, setNotifications] = useState<Notif[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getCookie("client_token");
    if (!token) { router.push("/lk/login"); return; }
    fetch(`${API}/cabinet/notifications`, { headers: hdr() })
      .then(r => r.json())
      .then(d => { setNotifications(d.notifications || []); setUnread(d.unread_count || 0); })
      .catch(() => router.push("/lk/login"))
      .finally(() => setLoading(false));
  }, [router]);

  async function markAllRead() {
    await fetch(`${API}/cabinet/notifications/read-all`, { method: "POST", headers: hdr() });
    setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
    setUnread(0);
  }

  if (loading) return <div className="py-12 text-center text-text-muted">Загрузка...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-text">Уведомления</h1>
          {unread > 0 && <p className="text-sm text-primary mt-1">{unread} непрочитанных</p>}
        </div>
        {unread > 0 && (
          <button onClick={markAllRead} className="text-sm text-primary hover:text-primary-dark">
            Прочитать все
          </button>
        )}
      </div>

      {notifications.length === 0 ? (
        <div className="bg-white rounded-2xl border border-neutral p-8 text-center text-text-muted">
          Нет уведомлений
        </div>
      ) : (
        <div className="space-y-2">
          {notifications.map(n => (
            <div key={n.id} className={`bg-white rounded-xl border p-4 ${n.is_read ? "border-neutral" : "border-primary/20 bg-primary/10"}`}>
              <div className="flex items-start gap-3">
                {!n.is_read && <div className="w-2 h-2 bg-primary rounded-full mt-1.5 flex-shrink-0" />}
                <div className="flex-1">
                  <p className={`text-sm ${n.is_read ? "text-text-body" : "text-text font-medium"}`}>{n.title}</p>
                  {n.body && <p className="text-xs text-text-muted mt-1">{n.body}</p>}
                  <p className="text-xs text-text-muted mt-2">
                    {new Date(n.date).toLocaleDateString("ru-RU", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" })}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
