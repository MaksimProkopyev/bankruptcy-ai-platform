"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LayoutList, CheckCircle, BarChart3, LogOut } from "lucide-react";
import { getProspects } from "@/lib/api";

const NAV = [
  { href: "/leads", label: "Лиды", icon: LayoutList },
  { href: "/prospects", label: "Подтверждение", icon: CheckCircle, badge: true },
  { href: "/stats", label: "Статистика", icon: BarChart3 },
];

export default function LeadgenSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [pendingCount, setPendingCount] = useState(0);
  const [userName, setUserName] = useState("");

  useEffect(() => {
    // Load pending prospects count
    getProspects()
      .then(data => setPendingCount(data.length))
      .catch(() => {});

    // Load user name from cookie
    const match = document.cookie.match(/staff_name=([^;]+)/);
    if (match) setUserName(decodeURIComponent(match[1]));
  }, []);

  function logout() {
    document.cookie = "staff_token=; path=/; max-age=0";
    document.cookie = "staff_name=; path=/; max-age=0";
    document.cookie = "staff_email=; path=/; max-age=0";
    localStorage.removeItem("token");
    router.push("/login");
  }

  return (
    <aside className="w-60 shrink-0 bg-primary flex flex-col min-h-screen">
      {/* Logo */}
      <div className="px-5 py-6 border-b border-border-dark">
        <div className="text-text-on-dark font-heading font-bold text-lg">Банкротство.AI</div>
        <div className="text-text-on-dark-muted text-xs mt-0.5">Лидогенерация</div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ href, label, icon: Icon, badge }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <a
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? "bg-accent text-text-on-dark"
                  : "text-text-on-dark-muted hover:bg-white/10 hover:text-text-on-dark"
              }`}
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span className="flex-1">{label}</span>
              {badge && pendingCount > 0 && (
                <span className="bg-danger text-white text-xs px-1.5 py-0.5 rounded-full font-bold">
                  {pendingCount}
                </span>
              )}
            </a>
          );
        })}
      </nav>

      {/* User + logout */}
      <div className="px-3 pb-5 border-t border-border-dark pt-4">
        {userName && (
          <div className="px-3 py-2 text-xs text-text-on-dark-muted truncate mb-2">{userName}</div>
        )}
        <button
          onClick={logout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm text-text-on-dark-muted hover:bg-white/10 hover:text-text-on-dark transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Выйти
        </button>
      </div>
    </aside>
  );
}
