"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const SITE_NAV = [
  { href: "/uslugi", label: "Услуги" },
  { href: "/o-kompanii", label: "О компании" },
  { href: "/blog", label: "Блог" },
  { href: "/faq", label: "Вопросы" },
  { href: "/kontakty", label: "Контакты" },
];

const LK_NAV = [
  { href: "/lk", label: "Моё дело" },
  { href: "/lk/dokumenty", label: "Документы" },
  { href: "/lk/kreditory", label: "Кредиторы" },
  { href: "/lk/yurist", label: "Мой юрист" },
  { href: "/lk/chat", label: "AI-ассистент" },
];

export default function SiteNavbar() {
  const pathname = usePathname();
  const [isClient, setIsClient] = useState(false);
  const [clientName, setClientName] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const token = getCookie("client_token");
    const name = getCookie("client_name");
    if (token) {
      setIsClient(true);
      setClientName(name || "");
    }
  }, []);

  const isLk = pathname.startsWith("/lk");
  const navItems = isLk && isClient ? LK_NAV : SITE_NAV;

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-neutral">
      <div className="max-w-6xl mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <span className="text-xl font-bold text-primary font-heading">Банкротство</span>
            <span className="text-xs text-accent font-medium px-1.5 py-0.5 bg-accent-light rounded">.AI</span>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => (
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
            <a
              href="tel:+78001234567"
              className="hidden lg:block text-sm text-text-muted hover:text-text"
            >
              8 800 123-45-67
            </a>

            {isClient ? (
              <div className="flex items-center gap-3">
                {!isLk && (
                  <Link
                    href="/lk"
                    className="px-4 py-2 text-sm bg-accent text-text-on-dark rounded-lg hover:bg-accent-hover shadow-card"
                  >
                    Личный кабинет
                  </Link>
                )}
                {isLk && (
                  <>
                    <span className="text-sm text-text-muted">{clientName}</span>
                    <button
                      onClick={() => {
                        deleteCookie("client_token");
                        deleteCookie("client_name");
                        window.location.href = "/";
                      }}
                      className="text-sm text-text-muted hover:text-text"
                    >
                      Выйти
                    </button>
                  </>
                )}
              </div>
            ) : (
              <Link
                href="/lk/login"
                className="px-4 py-2 text-sm bg-accent text-text-on-dark rounded-lg hover:bg-accent-hover shadow-card"
              >
                Личный кабинет
              </Link>
            )}

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
            {navItems.map((item) => (
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

// Cookie helpers (no dependencies)
function getCookie(name: string): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : "";
}

function deleteCookie(name: string) {
  document.cookie = `${name}=; path=/; max-age=0`;
}
