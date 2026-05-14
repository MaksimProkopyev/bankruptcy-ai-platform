"use client";

import { useState } from "react";

const DOC_TYPE_LABELS: Record<string, string> = {
  passport: "Паспорт",
  snils: "СНИЛС",
  inn_cert: "ИНН",
  income_2ndfl: "2-НДФЛ",
  bank_statement: "Выписка по счёту",
  credit_report: "Кредитный отчёт",
  credit_contract: "Кредитный договор",
  egrn_extract: "Выписка ЕГРН",
  vehicle_title: "ПТС",
  bankruptcy_application: "Заявление о банкротстве",
  court_ruling: "Определение суда",
  creditors_registry: "Реестр кредиторов",
  other: "Прочее",
};

const STATUS_STYLES: Record<string, { label: string; color: string }> = {
  pending: { label: "Ожидает", color: "bg-surface-muted text-text-muted" },
  uploaded: { label: "Загружен", color: "bg-info/10 text-info" },
  processing: { label: "Обработка AI", color: "bg-warning/10 text-warning" },
  extracted: { label: "Данные извлечены", color: "bg-primary/10 text-primary" },
  validated: { label: "Проверен", color: "bg-success/10 text-success" },
  rejected: { label: "Отклонён", color: "bg-danger/10 text-danger" },
};

export default function DocumentsPage() {
  const [search, setSearch] = useState("");

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Документы</h1>
      </div>

      <div className="mb-6">
        <input
          type="text"
          placeholder="Поиск по имени файла или типу..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full max-w-md px-4 py-2.5 border border-gray-200 rounded-lg text-sm bg-white"
        />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="text-sm font-medium text-gray-700 mb-3">Типы документов</h2>
        <div className="flex flex-wrap gap-2">
          {Object.entries(DOC_TYPE_LABELS).map(([key, label]) => (
            <span key={key} className="px-2.5 py-1 text-xs bg-gray-50 border border-gray-200 rounded-full text-gray-600">
              {label}
            </span>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="text-sm font-medium text-gray-700 mb-3">Статусы обработки</h2>
        <div className="flex flex-wrap gap-3">
          {Object.entries(STATUS_STYLES).map(([key, { label, color }]) => (
            <span key={key} className={`px-2.5 py-1 text-xs rounded-full font-medium ${color}`}>
              {label}
            </span>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
        <p className="text-gray-500 text-sm">
          Документы отображаются в карточке каждого дела.
          Здесь будет глобальный поиск и фильтрация по всем документам.
        </p>
        <p className="text-gray-400 text-xs mt-2">
          Откройте любое дело → вкладка «Документы» для загрузки и просмотра.
        </p>
      </div>
    </div>
  );
}
