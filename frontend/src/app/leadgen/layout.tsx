"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/leadgen/pipeline", label: "Воронка", icon: "🎯" },
  { href: "/leadgen/prospects", label: "Prospects", icon: "📋" },
  { href: "/leadgen/stats", label: "Статистика", icon: "📊" },
];

export default function LeadgenLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen">
      <aside
        className="w-60 min-h-screen flex flex-col flex-shrink-0"
        style={{ background: "#0F2640" }}
      >
        <div
          className="p-6 border-b"
          style={{ borderColor: "rgba(255,255,255,0.1)" }}
        >
          <Link href="/leadgen/pipeline">
            <h1
              className="text-lg font-semibold text-accent"
              style={{ fontFamily: "Georgia, serif" }}
            >
              Лидогенерация
            </h1>
            <p className="text-xs mt-1" style={{ color: "#D4E4F7" }}>
              Управление лидами
            </p>
          </Link>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
                  isActive
                    ? "font-medium text-white"
                    : "hover:text-white transition-colors"
                )}
                style={
                  isActive
                    ? { background: "#C9A84C", color: "#fff" }
                    : { color: "#D4E4F7" }
                }
              >
                <span className="text-base">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div
          className="p-4 border-t"
          style={{ borderColor: "rgba(255,255,255,0.1)" }}
        >
          <Link
            href="/crm"
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors"
            style={{ color: "#D4E4F7" }}
          >
            <span>←</span> CRM
          </Link>
        </div>
      </aside>

      <main className="flex-1 p-6 min-w-0" style={{ background: "#F8F7F4" }}>
        {children}
      </main>
    </div>
  );
}
