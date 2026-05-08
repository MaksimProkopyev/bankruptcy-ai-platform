"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
function getCookie(n: string) { if (typeof document === "undefined") return ""; const m = document.cookie.match(new RegExp("(^| )" + n + "=([^;]+)")); return m ? decodeURIComponent(m[2]) : ""; }

const TYPE_LABELS: Record<string, string> = { bank: "Банк", mfo: "МФО", individual: "Физлицо", tax_authority: "ФНС", utility: "ЖКХ", other: "Прочее" };

interface Creditor { name: string; type: string; total_amount: number; principal: number | null; interest: number | null; penalty: number | null; is_secured: boolean; in_registry: boolean; contract_number: string | null; }
interface Summary { total_debt: number; secured_debt: number; unsecured_debt: number; count: number; in_registry: number; }

export default function LkCreditorsPage() {
  const router = useRouter();
  const [creditors, setCreditors] = useState<Creditor[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getCookie("client_token");
    if (!token) { router.push("/lk/login"); return; }
    fetch(`${API}/cabinet/creditors`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => { setCreditors(d.creditors || []); setSummary(d.summary || null); })
      .catch(() => router.push("/lk/login"))
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) return <div className="py-12 text-center text-gray-400">Загрузка...</div>;

  return (
    <div>
      <h1 className="text-xl font-semibold text-gray-900 mb-6">Кредиторы</h1>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-2xl border border-gray-200 p-4">
            <p className="text-xs text-gray-400">Общий долг</p>
            <p className="text-lg font-semibold text-gray-900 mt-1">{summary.total_debt.toLocaleString("ru-RU")} ₽</p>
          </div>
          <div className="bg-white rounded-2xl border border-gray-200 p-4">
            <p className="text-xs text-gray-400">Кредиторов</p>
            <p className="text-lg font-semibold text-gray-900 mt-1">{summary.count}</p>
          </div>
          <div className="bg-white rounded-2xl border border-gray-200 p-4">
            <p className="text-xs text-gray-400">В реестре</p>
            <p className="text-lg font-semibold text-green-600 mt-1">{summary.in_registry}</p>
          </div>
          <div className="bg-white rounded-2xl border border-gray-200 p-4">
            <p className="text-xs text-gray-400">Залоговые</p>
            <p className="text-lg font-semibold text-orange-600 mt-1">{summary.secured_debt > 0 ? summary.secured_debt.toLocaleString("ru-RU") + " ₽" : "—"}</p>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {creditors.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-200 p-8 text-center text-gray-400">Нет данных о кредиторах</div>
        ) : creditors.map((c, i) => (
          <div key={i} className={`bg-white rounded-2xl border p-5 ${c.is_secured ? "border-orange-200" : "border-gray-200"}`}>
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-gray-900">{c.name}</h3>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">{TYPE_LABELS[c.type] || c.type}</span>
                  {c.is_secured && <span className="text-xs px-2 py-0.5 rounded-full bg-orange-100 text-orange-700">Залоговый</span>}
                  {c.in_registry && <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">В реестре</span>}
                </div>
                {c.contract_number && <p className="text-xs text-gray-400 mt-1">Договор {c.contract_number}</p>}
              </div>
              <p className="text-base font-bold text-gray-900">{c.total_amount.toLocaleString("ru-RU")} ₽</p>
            </div>
            {(c.principal || c.interest || c.penalty) && (
              <div className="flex gap-6 mt-3 text-xs text-gray-500">
                {c.principal && <span>Основной: {c.principal.toLocaleString("ru-RU")} ₽</span>}
                {c.interest && <span>Проценты: {c.interest.toLocaleString("ru-RU")} ₽</span>}
                {c.penalty && <span>Штрафы: {c.penalty.toLocaleString("ru-RU")} ₽</span>}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-6 bg-blue-50 rounded-2xl p-5">
        <p className="text-sm text-blue-800">После введения процедуры банкротства кредиторы не могут предъявлять вам требования напрямую. Все вопросы решаются через финансового управляющего и суд.</p>
      </div>
    </div>
  );
}
