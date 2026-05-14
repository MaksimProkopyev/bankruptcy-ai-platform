"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import LkNavbar from "@/components/layout/LkNavbar";
import "./globals.css";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function getCookie(n: string) {
  if (typeof document === "undefined") return "";
  const m = document.cookie.match(new RegExp("(^| )" + n + "=([^;]+)"));
  return m ? decodeURIComponent(m[2]) : "";
}

const LK_NAV = [
  { href: "/dashboard", label: "Моё дело", icon: "📋", exact: true },
  { href: "/dokumenty", label: "Документы", icon: "📄" },
  { href: "/podpis", label: "Подписание", icon: "✍️" },
  { href: "/kreditory", label: "Кредиторы", icon: "🏦" },
  { href: "/oplaty", label: "Оплаты", icon: "💳" },
  { href: "/konsultacii", label: "Консультации", icon: "📞" },
  { href: "/chat", label: "Чат", icon: "💬" },
  { href: "/kalendar", label: "Календарь", icon: "📅" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    const token = getCookie("client_token");
    if (!token) return;
    fetch(`${API}/cabinet/notifications`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => setUnread(d.unread_count || 0))
      .catch(() => {});
  }, [pathname]);

  if (pathname === "/login") {
    return (
      <html lang="ru">
        <body className="antialiased">{children}</body>
      </html>
    );
  }

  return (
    <html lang="ru">
      <body className="antialiased">
        <div className="min-h-screen bg-surface">
          <LkNavbar />
          <div className="max-w-6xl mx-auto px-6 py-8">
            <div className="flex gap-8">
              {/* Sidebar */}
              <aside className="hidden md:block w-56 flex-shrink-0">
                <nav className="space-y-1 sticky top-24">
                  {LK_NAV.map((item) => {
                    const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
                    return (
                      <Link key={item.href} href={item.href}
                        className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm transition-colors ${
                          active ? "bg-primary/10 text-primary font-medium" : "text-text-muted hover:bg-surface-muted"
                        }`}>
                        <span>{item.icon}</span>
                        {item.label}
                      </Link>
                    );
                  })}

                  {/* Notifications link with badge */}
                  <Link href="/uvedomleniya"
                    className={`flex items-center justify-between px-4 py-2.5 rounded-xl text-sm transition-colors ${
                      pathname === "/uvedomleniya" ? "bg-primary/10 text-primary font-medium" : "text-text-muted hover:bg-surface-muted"
                    }`}>
                    <span className="flex items-center gap-3"><span>🔔</span> Уведомления</span>
                    {unread > 0 && (
                      <span className="w-5 h-5 bg-danger text-text-on-dark text-[10px] font-bold rounded-full flex items-center justify-center">{unread}</span>
                    )}
                  </Link>
                </nav>
              </aside>

              {/* Main */}
              <main className="flex-1 min-w-0">{children}</main>
            </div>
          </div>
        </div>
      </body>
    </html>
  );
}
