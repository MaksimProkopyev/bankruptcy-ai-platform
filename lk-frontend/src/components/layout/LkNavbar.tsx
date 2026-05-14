"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LK_NAV = [
  { href: "/dashboard", label: "Моё дело" },
  { href: "/dokumenty", label: "Документы" },
  { href: "/kreditory", label: "Кредиторы" },
  { href: "/konsultacii", label: "Консультации" },
  { href: "/chat", label: "AI-ассистент" },
];

export default function LkNavbar() {
  const pathname = usePathname();
  const [clientName, setClientName] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const name = getCookie("client_name");
    if (name) setClientName(name);
  }, []);

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-neutral">
      <div className="max-w-6xl mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/dashboard" className="flex items-center gap-2">
            <span className="text-xl font-bold text-primary font-heading">Банкротство</span>
            <span className="text-xs text-accent font-medium px-1.5 py-0.5 bg-accent-light rounded">.AI</span>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-1">
            {LK_NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`px-3 py-2 text-sm rounded-lg transition-colors ${
                  pathname === item.href
                    ? "text-accent bg-accent-light font-medium"
                    : "text-text-body hover:text-text hover:bg-surface-muted"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          {/* Right section */}
          <div className="flex items-center gap-3">
            {clientName && (
              <span className="hidden lg:block text-sm text-text-muted">{clientName}</span>
            )}
            <button
              onClick={() => {
                deleteCookie("client_token");
                deleteCookie("client_name");
                window.location.href = "/login";
              }}
              className="text-sm text-text-muted hover:text-text"
            >
              Выйти
            </button>

            {/* Mobile menu button */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden w-10 h-10 flex items-center justify-center rounded-lg hover:bg-surface-muted"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                {mobileOpen ? (
                  <path d="M18 6L6 18M6 6l12 12" />
                ) : (
                  <path d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileOpen && (
          <div className="md:hidden py-4 border-t border-neutral">
            {LK_NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className="block px-3 py-2.5 text-sm text-text-body hover:bg-surface-muted rounded-lg"
              >
                {item.label}
              </Link>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}

function getCookie(name: string): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : "";
}

function deleteCookie(name: string) {
  document.cookie = `${name}=; path=/; max-age=0`;
}
