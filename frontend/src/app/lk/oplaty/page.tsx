"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function getCookie(name: string): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : "";
}

interface PaymentItem {
  id: string;
  payment_type: string;
  amount: number;
  status: string;
  due_date?: string;
  paid_date?: string;
  invoice_number?: string;
}

const TYPE_LABELS: Record<string, string> = {
  service_fee: "Услуги юриста",
  court_fee: "Госпошлина",
  fu_deposit: "Депозит ФУ (25 000 ₽)",
  publication_fee: "Публикации (ЕФРСБ, Коммерсантъ)",
  other: "Прочее",
};

const STATUS_STYLES: Record<string, { label: string; color: string }> = {
  pending: { label: "К оплате", color: "bg-yellow-100 text-yellow-700" },
  paid: { label: "Оплачено", color: "bg-green-100 text-green-700" },
  overdue: { label: "Просрочено", color: "bg-red-100 text-red-700" },
  cancelled: { label: "Отменено", color: "bg-gray-100 text-gray-500" },
};

export default function LkPaymentsPage() {
  const router = useRouter();
  const [payments, setPayments] = useState<PaymentItem[]>([]);
  const [totalPaid, setTotalPaid] = useState(0);
  const [totalPending, setTotalPending] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getCookie("client_token");
    if (!token) { router.push("/lk/login"); return; }

    fetch(`${API_URL}/cabinet/payments`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        setPayments(data.payments || []);
        setTotalPaid(data.total_paid || 0);
        setTotalPending(data.total_pending || 0);
      })
      .catch(() => router.push("/lk/login"))
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) return <div className="py-12 text-center text-text-muted">Загрузка...</div>;

  return (
    <div>
      <h1 className="text-xl font-semibold text-text mb-6">Оплаты</h1>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-2xl border border-neutral p-5">
          <p className="text-sm text-text-muted">Оплачено</p>
          <p className="text-xl font-semibold text-success mt-1">
            {totalPaid.toLocaleString("ru-RU")} ₽
          </p>
        </div>
        <div className="bg-white rounded-2xl border border-neutral p-5">
          <p className="text-sm text-text-muted">К оплате</p>
          <p className="text-xl font-semibold text-text mt-1">
            {totalPending.toLocaleString("ru-RU")} ₽
          </p>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-neutral">
        {payments.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-text-muted text-sm">Нет записей об оплатах</p>
            <p className="text-text-muted text-xs mt-1">Счета появятся после подписания договора</p>
          </div>
        ) : (
          <div className="divide-y divide-neutral">
            {payments.map((p) => (
              <div key={p.id} className="px-6 py-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-text">
                    {TYPE_LABELS[p.payment_type] || p.payment_type}
                  </p>
                  <p className="text-xs text-text-muted mt-0.5">
                    {p.invoice_number ? `Счёт ${p.invoice_number}` : ""}
                    {p.due_date ? ` · до ${new Date(p.due_date).toLocaleDateString("ru-RU")}` : ""}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium text-text">
                    {p.amount.toLocaleString("ru-RU")} ₽
                  </p>
                  <span className={`inline-block mt-1 px-2 py-0.5 text-xs rounded-full ${
                    STATUS_STYLES[p.status]?.color || "bg-surface-muted text-text-muted"
                  }`}>
                    {STATUS_STYLES[p.status]?.label || p.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-6 bg-primary/10 rounded-2xl p-5">
        <h3 className="text-sm font-medium text-primary-dark mb-2">Способы оплаты</h3>
        <p className="text-sm text-primary">
          Оплата банковской картой или переводом по реквизитам.
          По вопросам: 8 800 123-45-67.
        </p>
      </div>
    </div>
  );
}
