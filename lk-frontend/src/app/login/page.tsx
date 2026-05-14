"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function LkLoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect") || "/dashboard";

  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function sendCode() {
    setError(""); setLoading(true);
    try {
      const res = await fetch(`${API_URL}/client-auth/send-code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone }),
      });
      if (!res.ok) throw new Error("Ошибка отправки");
      setStep("code");
    } catch (err: any) { setError(err.message); }
    finally { setLoading(false); }
  }

  async function verifyCode() {
    setError(""); setLoading(true);
    try {
      const res = await fetch(`${API_URL}/client-auth/verify-code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, code }),
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail || "Неверный код"); }
      const data = await res.json();

      // Store in cookies (accessible by middleware)
      document.cookie = `client_token=${data.access_token}; path=/; max-age=86400; SameSite=Lax`;
      document.cookie = `client_name=${encodeURIComponent(data.client_name)}; path=/; max-age=86400; SameSite=Lax`;

      router.push(redirect);
    } catch (err: any) { setError(err.message); }
    finally { setLoading(false); }
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center">
      <div className="w-full max-w-sm px-6">
        <div className="text-center mb-8">
          <Link href="/" className="text-2xl font-bold text-primary">Банкротство.AI</Link>
          <p className="text-sm text-text-muted mt-2">Вход в личный кабинет</p>
        </div>

        <div className="bg-white p-8 rounded-2xl border border-neutral shadow-card">
          {error && <div className="mb-4 p-3 bg-danger/10 border border-danger rounded-xl text-sm text-danger">{error}</div>}

          {step === "phone" ? (
            <>
              <label className="block text-sm font-medium text-text-body mb-1.5">Номер телефона</label>
              <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
                placeholder="+7 900 123-45-67"
                className="w-full px-4 py-3 border border-neutral rounded-xl text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-primary" />
              <button onClick={sendCode} disabled={loading || phone.length < 10}
                className="w-full py-3 bg-accent text-text-on-dark rounded-xl text-sm font-medium hover:bg-accent-hover disabled:opacity-50">
                {loading ? "Отправка..." : "Получить код"}
              </button>
            </>
          ) : (
            <>
              <p className="text-sm text-text-muted mb-4">Код отправлен на <span className="font-medium">{phone}</span></p>
              <input type="text" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="000000" maxLength={6} autoFocus
                className="w-full px-4 py-3 border border-neutral rounded-xl text-center text-lg tracking-widest mb-4 focus:outline-none focus:ring-2 focus:ring-primary" />
              <button onClick={verifyCode} disabled={loading || code.length !== 6}
                className="w-full py-3 bg-accent text-text-on-dark rounded-xl text-sm font-medium hover:bg-accent-hover disabled:opacity-50">
                {loading ? "Проверка..." : "Войти"}
              </button>
              <button onClick={() => { setStep("phone"); setCode(""); }} className="w-full mt-3 text-sm text-text-muted hover:text-text-body">
                Изменить номер
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

import { Suspense } from "react";
export default function LkLoginPage() {
  return <Suspense><LkLoginPageContent /></Suspense>;
}
