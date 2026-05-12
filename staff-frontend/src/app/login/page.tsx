"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (res.status === 401 || res.status === 403) {
        setError("Неверный email или пароль");
        return;
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Ошибка входа");
        return;
      }
      const data = await res.json();
      const token: string = data.access_token;
      // Save token as cookie
      document.cookie = `staff_token=${encodeURIComponent(token)}; path=/; SameSite=Strict`;
      router.push("/dashboard");
    } catch {
      setError("Ошибка соединения с сервером");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#F8F7F4] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold font-heading text-[#1B3A5C]">
            НССБ «Максимум»
          </h1>
          <p className="text-sm text-gray-500 mt-2">Портал сотрудников</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 space-y-4"
        >
          <div>
            <label className="block text-sm text-gray-600 mb-1.5">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              placeholder="you@company.ru"
              className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-[#1B3A5C] bg-white transition-colors"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-600 mb-1.5">Пароль</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              placeholder="••••••••"
              className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-[#1B3A5C] bg-white transition-colors"
            />
          </div>

          {error && (
            <p className="text-sm text-red-500 bg-red-50 px-3 py-2 rounded-lg">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 text-sm font-medium bg-[#1B3A5C] text-[#C9A84C] rounded-lg hover:bg-[#142d48] disabled:opacity-60 transition-colors mt-2"
          >
            {loading ? "Вход..." : "Войти"}
          </button>
        </form>
      </div>
    </div>
  );
}
