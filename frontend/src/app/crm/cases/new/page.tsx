"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { clients as clientsApi, cases as casesApi, type ClientCreate } from "@/lib/api";

export default function NewCasePage() {
  const router = useRouter();
  const [step, setStep] = useState<"client" | "case">("client");
  const [clientId, setClientId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [client, setClient] = useState<ClientCreate>({
    first_name: "",
    last_name: "",
    phone: "",
    email: "",
    region: "",
    lead_source: "website",
  });

  const [totalDebt, setTotalDebt] = useState("");
  const [notes, setNotes] = useState("");

  async function handleCreateClient(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const created = await clientsApi.create(client);
      setClientId(created.id);
      setStep("case");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateCase(e: React.FormEvent) {
    e.preventDefault();
    if (!clientId) return;
    setError("");
    setLoading(true);
    try {
      const created = await casesApi.create({
        client_id: clientId,
        total_debt: totalDebt ? parseFloat(totalDebt) : undefined,
        notes: notes || undefined,
      });
      router.push(`/cases/${created.id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <Link href="/crm/cases" className="text-sm text-gray-400 hover:text-gray-600 mb-4 block">
        ← Все дела
      </Link>
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Новое дело</h1>

      {/* Steps indicator */}
      <div className="flex items-center gap-3 mb-8">
        <div className={`flex items-center gap-2 ${step === "client" ? "text-brand-600" : "text-green-600"}`}>
          <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium ${step === "client" ? "bg-brand-100 text-brand-700" : "bg-green-100 text-green-700"}`}>
            {step === "case" ? "✓" : "1"}
          </span>
          <span className="text-sm font-medium">Клиент</span>
        </div>
        <div className="w-8 h-px bg-gray-200" />
        <div className={`flex items-center gap-2 ${step === "case" ? "text-brand-600" : "text-gray-400"}`}>
          <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium ${step === "case" ? "bg-brand-100 text-brand-700" : "bg-gray-100 text-gray-400"}`}>
            2
          </span>
          <span className="text-sm font-medium">Дело</span>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
      )}

      {step === "client" && (
        <form onSubmit={handleCreateClient} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <h2 className="text-lg font-medium text-gray-900 mb-2">Данные клиента</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Фамилия *</label>
              <input type="text" required value={client.last_name} onChange={(e) => setClient({ ...client, last_name: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Имя *</label>
              <input type="text" required value={client.first_name} onChange={(e) => setClient({ ...client, first_name: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Телефон *</label>
              <input type="tel" required value={client.phone} onChange={(e) => setClient({ ...client, phone: e.target.value })} placeholder="+79001234567" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input type="email" value={client.email} onChange={(e) => setClient({ ...client, email: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Регион</label>
              <input type="text" value={client.region} onChange={(e) => setClient({ ...client, region: e.target.value })} placeholder="Москва" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Источник</label>
              <select value={client.lead_source} onChange={(e) => setClient({ ...client, lead_source: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                <option value="website">Сайт</option>
                <option value="telegram">Telegram</option>
                <option value="whatsapp">WhatsApp</option>
                <option value="phone">Телефон</option>
                <option value="referral">Рекомендация</option>
              </select>
            </div>
          </div>
          <button type="submit" disabled={loading} className="px-6 py-2.5 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50">
            {loading ? "Создание..." : "Далее →"}
          </button>
        </form>
      )}

      {step === "case" && (
        <form onSubmit={handleCreateCase} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <h2 className="text-lg font-medium text-gray-900 mb-2">Данные дела</h2>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Общая сумма долга (₽)</label>
            <input type="number" value={totalDebt} onChange={(e) => setTotalDebt(e.target.value)} placeholder="850000" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Заметки</label>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} placeholder="Дополнительная информация о клиенте..." className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          </div>
          <div className="flex gap-3">
            <button type="button" onClick={() => setStep("client")} className="px-4 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50">← Назад</button>
            <button type="submit" disabled={loading} className="px-6 py-2.5 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50">
              {loading ? "Создание..." : "Создать дело"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
