"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  LayoutDashboard,
  CheckSquare,
  Lightbulb,
  LogOut,
  Menu,
  X,
} from "lucide-react";
import { clsx } from "clsx";
import { getUser, logout } from "@/lib/auth";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Мой кабинет", icon: LayoutDashboard },
  { href: "/tasks", label: "Задачи", icon: CheckSquare },
  { href: "/ideas", label: "Идеи", icon: Lightbulb },
];

const ROLE_LABELS: Record<string, string> = {
  lawyer: "Юрист",
  paralegal: "Помощник юриста",
  client_manager: "Клиентский менеджер",
  marketer: "Маркетолог",
  ai_engineer: "AI-инженер",
  admin: "Администратор",
  operations_director: "Директор операций",
};

export default function Sidebar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const user = getUser();
  const displayName =
    user
      ? [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email || "Сотрудник"
      : "Сотрудник";
  const roleLabel = user ? (ROLE_LABELS[user.role] ?? user.role) : "";

  const navContent = (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="p-6 border-b border-white/10">
        <h1 className="text-lg font-bold font-heading text-[#C9A84C]">
          НССБ «Максимум»
        </h1>
        <p className="text-xs text-white/50 mt-1">Портал сотрудников</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-4 space-y-1">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              onClick={() => setMobileOpen(false)}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
                isActive
                  ? "bg-white/10 text-[#C9A84C] font-medium"
                  : "text-white/70 hover:bg-white/5 hover:text-white"
              )}
            >
              <Icon size={18} className={isActive ? "text-[#C9A84C]" : ""} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* User + logout */}
      <div className="p-4 border-t border-white/10">
        <div className="mb-3 px-1">
          <p className="text-sm font-medium text-white truncate">{displayName}</p>
          <p className="text-xs text-white/50 truncate">{roleLabel}</p>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-2 w-full px-3 py-2 text-sm text-white/70 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
        >
          <LogOut size={16} />
          Выйти
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile hamburger */}
      <button
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-[#1B3A5C] text-white rounded-lg shadow-md"
        onClick={() => setMobileOpen((v) => !v)}
        aria-label="Меню"
      >
        {mobileOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/40 z-30"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar — desktop: fixed; mobile: slide-in */}
      <aside
        className={clsx(
          "fixed left-0 top-0 h-full w-60 bg-[#1B3A5C] z-40 flex flex-col transition-transform duration-200",
          "lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {navContent}
      </aside>
    </>
  );
}
