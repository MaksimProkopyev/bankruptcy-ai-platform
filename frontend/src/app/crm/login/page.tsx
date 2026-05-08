"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function CrmLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault(); setError(""); setLoading(true);
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw new Error("Неверный email или пароль");
      const { access_token } = await res.json();
      document.cookie = `staff_token=${access_token}; path=/; max-age=86400; SameSite=Lax`;
      localStorage.setItem("token", access_token);
      // Fetch user info for sidebar
      const me = await fetch(`${API_URL}/auth/me`, { headers: { Authorization: `Bearer ${access_token}` } });
      if (me.ok) {
        const user = await me.json();
        document.cookie = `staff_name=${encodeURIComponent(user.last_name + ' ' + user.first_name)}; path=/; max-age=86400`;
        document.cookie = `staff_email=${encodeURIComponent(user.email)}; path=/; max-age=86400`;
      }
      router.push("/crm");
    } catch (err: any) { setError(err.message); }
    finally { setLoading(false); }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface">
      <div className="w-full max-w-sm px-6">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-semibold text-text">Банкротство.AI</h1>
          <p className="text-sm text-text-muted mt-1">CRM — вход для сотрудников</p>
        </div>
        <form onSubmit={handleSubmit} className="bg-white p-8 rounded-2xl border border-neutral shadow-card">
          {error && <div className="mb-4 p-3 bg-danger/10 border border-danger rounded-xl text-sm text-danger">{error}</div>}
          <div className="mb-4">
            <label className="block text-sm font-medium text-text-body mb-1">Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
              placeholder="ivanov@bankruptcy.ai"
              className="w-full px-4 py-3 border border-neutral rounded-xl text-sm focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary" />
          </div>
          <div className="mb-6">
            <label className="block text-sm font-medium text-text-body mb-1">Пароль</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required
              className="w-full px-4 py-3 border border-neutral rounded-xl text-sm focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary" />
          </div>
          <button type="submit" disabled={loading}
            className="w-full py-3 bg-accent text-text-on-dark rounded-xl text-sm font-medium hover:bg-accent-hover disabled:opacity-50">
            {loading ? "Вход..." : "Войти в CRM"}
          </button>
        </form>
      </div>
    </div>
  );
}
