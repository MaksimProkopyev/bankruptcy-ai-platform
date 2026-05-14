"use client";
import { useEffect, useState } from "react";
import { formatCurrency, formatDate } from "@/lib/case-utils";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
function getToken() { if (typeof window === "undefined") return ""; return localStorage.getItem("token") || ""; }
function hdr() { return { Authorization: `Bearer ${getToken()}`, "Content-Type": "application/json" }; }

type Tab = "templates" | "drafts" | "invoices" | "signatures";

interface Template { id: string; name: string; slug: string; category: string; description: string; is_active: boolean; version: number; }

const STATUS_STYLES: Record<string, { label: string; color: string }> = {
  draft: { label: "Черновик", color: "bg-gray-100 text-gray-600" },
  review: { label: "На проверке", color: "bg-yellow-100 text-yellow-700" },
  approved: { label: "Утверждён", color: "bg-green-100 text-green-700" },
  sent_for_signing: { label: "На подписании", color: "bg-blue-100 text-blue-700" },
  signed: { label: "Подписан", color: "bg-green-100 text-green-700" },
  sent: { label: "Отправлен", color: "bg-blue-100 text-blue-700" },
  paid: { label: "Оплачен", color: "bg-green-100 text-green-700" },
  overdue: { label: "Просрочен", color: "bg-red-100 text-red-700" },
  reconciled: { label: "Сверен", color: "bg-teal-100 text-teal-700" },
};

export default function CrmBillingPage() {
  const [tab, setTab] = useState<Tab>("templates");
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    if (tab === "templates") {
      fetch(`${API}/billing/templates`, { headers: hdr() })
        .then(r => r.json()).then(d => setTemplates(Array.isArray(d) ? d : d.templates || [])).catch(() => {}).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [tab]);

  async function seedTemplates() {
    await fetch(`${API}/billing/templates/seed`, { method: "POST", headers: hdr() });
    const r = await fetch(`${API}/billing/templates`, { headers: hdr() });
    setTemplates(await r.json());
  }

  const TABS: { k: Tab; l: string; i: string }[] = [
    { k: "templates", l: "Шаблоны", i: "📋" },
    { k: "drafts", l: "Документы", i: "📄" },
    { k: "invoices", l: "Счета", i: "💳" },
    { k: "signatures", l: "Подписи", i: "✍️" },
  ];

  const CATEGORY_LABELS: Record<string, string> = {
    contract: "Договор", power_of_attorney: "Доверенность", act: "Акт",
    application: "Заявление", petition: "Ходатайство",
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Документооборот и биллинг</h1>
      </div>

      <div className="flex gap-1 mb-6 border-b border-neutral">
        {TABS.map(t => (
          <button key={t.k} onClick={() => setTab(t.k)}
            className={`px-4 py-2.5 text-sm border-b-2 ${tab === t.k ? "border-primary text-primary font-medium" : "border-transparent text-text-muted"}`}>
            <span className="mr-1.5">{t.i}</span>{t.l}
          </button>
        ))}
      </div>

      {tab === "templates" && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <p className="text-sm text-gray-500">Шаблоны с переменными — AI автозаполняет из данных дела</p>
            <button onClick={seedTemplates} className="px-4 py-2 text-sm bg-accent text-text-on-dark rounded-lg hover:bg-accent-hover">
              Загрузить шаблоны
            </button>
          </div>
          {loading ? <p className="text-gray-400">Загрузка...</p> : templates.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
              <p className="text-gray-500">Шаблоны не загружены</p>
              <p className="text-xs text-gray-400 mt-1">Нажмите «Загрузить шаблоны» для инициализации</p>
            </div>
          ) : (
            <div className="space-y-3">
              {templates.map(t => (
                <div key={t.id} className="bg-white rounded-xl border border-gray-200 p-5 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-semibold text-gray-900">{t.name}</h3>
                      <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">
                        {CATEGORY_LABELS[t.category] || t.category}
                      </span>
                      <span className="text-xs text-gray-400">v{t.version}</span>
                    </div>
                    {t.description && <p className="text-xs text-gray-500 mt-1">{t.description}</p>}
                  </div>
                  <div className="flex gap-2">
                    <button className="px-3 py-1.5 text-xs bg-primary/10 text-primary rounded-lg hover:bg-primary/20">
                      Создать документ
                    </button>
                    <button className="px-3 py-1.5 text-xs bg-gray-50 text-gray-600 rounded-lg hover:bg-gray-100">
                      Редактировать
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="mt-6 bg-primary/10 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-primary-dark mb-3">Как работает документооборот</h3>
            <div className="flex items-center gap-3 text-xs text-primary">
              {["Шаблон", "→ AI заполняет", "→ Юрист проверяет", "→ Клиент подписывает (SMS)", "→ Архив"].map((s, i) => (
                <span key={i} className={i === 0 || i === 4 ? "font-semibold" : ""}>{s}</span>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === "drafts" && (
        <div>
          <p className="text-sm text-gray-500 mb-4">Сгенерированные документы по делам</p>
          <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
            <p className="text-gray-500">Документы появятся после генерации из шаблонов</p>
            <p className="text-xs text-gray-400 mt-1">Откройте дело → «Создать документ» → выберите шаблон</p>
          </div>
        </div>
      )}

      {tab === "invoices" && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <p className="text-sm text-gray-500">Счета выставляются автоматически через банк Точка</p>
            <button className="px-4 py-2 text-sm bg-accent text-text-on-dark rounded-lg">+ Выставить счёт</button>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-lg">🏦</span>
              <div>
                <p className="text-sm font-medium text-gray-900">Банк Точка</p>
                <p className="text-xs text-gray-400">Автосчета, webhook сверка, выписки</p>
              </div>
            </div>
            <span className="px-2.5 py-1 text-xs rounded-full bg-yellow-100 text-yellow-700 font-medium">
              Нужен API-токен
            </span>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
            <p className="text-gray-500">Нет выставленных счетов</p>
          </div>

          <div className="mt-4 bg-teal-50 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-teal-900 mb-2">Автоматизация Точка</h3>
            <div className="text-xs text-teal-700 space-y-1">
              <p>• Договор подписан → счёт выставляется автоматически</p>
              <p>• Деньги пришли → webhook обновляет статус в CRM</p>
              <p>• Этап завершён → акт генерируется и отправляется на подпись</p>
              <p>• Ежедневная сверка выписок для бухгалтерии</p>
            </div>
          </div>
        </div>
      )}

      {tab === "signatures" && (
        <div>
          <p className="text-sm text-gray-500 mb-4">Аудит-трейл электронных подписей</p>
          <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Типы подписей в системе</h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="p-4 bg-green-50 rounded-xl border border-green-200">
                <p className="text-sm font-semibold text-green-800">Простая ЭП (SMS)</p>
                <p className="text-xs text-green-600 mt-1">Договоры, акты, согласия</p>
                <p className="text-xs text-green-500 mt-2">✅ Активна</p>
              </div>
              <div className="p-4 bg-blue-50 rounded-xl border border-blue-200">
                <p className="text-sm font-semibold text-blue-800">УКЭП юриста</p>
                <p className="text-xs text-blue-600 mt-1">Мой Арбитр, суд</p>
                <p className="text-xs text-blue-500 mt-2">✅ Внешняя (КриптоПро)</p>
              </div>
              <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                <p className="text-sm font-semibold text-gray-700">Госключ (УНЭП)</p>
                <p className="text-xs text-gray-500 mt-1">Клиентская УНЭП</p>
                <p className="text-xs text-gray-400 mt-2">Запланировано (V2)</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
            <p className="text-gray-500">Нет записей подписей</p>
            <p className="text-xs text-gray-400 mt-1">Аудит-трейл появится после первого подписания документа</p>
          </div>
        </div>
      )}
    </div>
  );
}
