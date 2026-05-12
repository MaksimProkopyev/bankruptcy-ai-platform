"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clsx } from "clsx";

const NAV_ITEMS = [
  { href: "/crm", label: "Дашборд", icon: "📊", staffOnly: false },
  { href: "/crm/cases", label: "Дела", icon: "📁", staffOnly: false },
  { href: "/crm/prospects", label: "Лидогенерация", icon: "🔍", staffOnly: false },
  { href: "/crm/clients", label: "Клиенты", icon: "👤", staffOnly: false },
  { href: "/crm/deadlines", label: "Сроки", icon: "⏰", staffOnly: false },
  { href: "/crm/documents", label: "Документы", icon: "📄", staffOnly: false },
  { href: "/crm/analytics", label: "Аналитика", icon: "📈", staffOnly: false },
  { href: "/crm/billing", label: "Документы/Счета", icon: "📝", staffOnly: false },
  { href: "/crm/settings", label: "Настройки", icon: "⚙️", staffOnly: false },
];

function getCookie(name: string): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : "";
}

function getUserRoleFromToken(): string {
  if (typeof window === "undefined") return "";
  try {
    const token = localStorage.getItem("token");
    if (!token) return "";
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.role || "";
  } catch {
    return "";
  }
}

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const userName = getCookie("staff_name") || "Пользователь";
  const userEmail = getCookie("staff_email") || "";
  const userRole = getUserRoleFromToken();

  function handleLogout() {
    document.cookie = "staff_token=; path=/; max-age=0";
    document.cookie = "staff_name=; path=/; max-age=0";
    document.cookie = "staff_email=; path=/; max-age=0";
    router.push("/crm/login");
  }

  return (
    <aside className="w-64 bg-primary-dark border-r border-border-dark min-h-screen flex flex-col">
      <div className="p-6 border-b border-border-dark">
        <Link href="/crm">
          <h1 className="text-lg font-semibold text-accent font-heading">Банкротство.AI</h1>
          <p className="text-xs text-text-on-dark-muted mt-1">CRM · Управление делами</p>
        </Link>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {NAV_ITEMS.filter((item) => {
          if (item.staffOnly && userRole === "client") return false;
          return true;
        }).map((item) => {
          const isActive = item.href === "/crm"
            ? pathname === "/crm"
            : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
                isActive
                  ? "bg-primary text-accent font-medium"
                  : "text-text-on-dark-muted hover:bg-primary hover:text-text-on-dark"
              )}
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-border-dark">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center text-text-on-dark text-sm font-medium flex-shrink-0">
              {userName.charAt(0)}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-text-on-dark truncate">{userName}</p>
              {userEmail && <p className="text-xs text-text-on-dark-muted truncate">{userEmail}</p>}
            </div>
          </div>
          <button onClick={handleLogout} className="text-xs text-text-on-dark-muted hover:text-text-on-dark flex-shrink-0" title="Выйти">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/></svg>
          </button>
        </div>
      </div>
    </aside>
  );
}
