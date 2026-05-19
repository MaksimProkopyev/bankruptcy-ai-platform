"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GlobalDocument {
  id: string;
  file_name: string | null;
  document_type: string;
  status: string;
  case_id: string;
  case_number: string | null;
  client_name: string;
  created_at: string;
  download_url: string | null;
}

interface DocsPage {
  items: GlobalDocument[];
  total: number;
  page: number;
  per_page: number;
}

// ---------------------------------------------------------------------------
// Label maps
// ---------------------------------------------------------------------------

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
  pending: { label: "Ожидает", color: "bg-gray-100 text-gray-600" },
  uploaded: { label: "Загружен", color: "bg-blue-100 text-blue-700" },
  processing: { label: "Обработка AI", color: "bg-yellow-100 text-yellow-700" },
  extracted: { label: "Данные извлечены", color: "bg-indigo-100 text-indigo-700" },
  validated: { label: "Проверен", color: "bg-green-100 text-green-700" },
  rejected: { label: "Отклонён", color: "bg-red-100 text-red-700" },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("token") || "";
}

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_STYLES[status] ?? { label: status, color: "bg-gray-100 text-gray-600" };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${s.color}`}>
      {s.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function DocumentsPage() {
  const [docs, setDocs] = useState<GlobalDocument[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const perPage = 50;
  const [loading, setLoading] = useState(true);
  const [fileType, setFileType] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchDocs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fileType, status, search, page]);

  function fetchDocs() {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    if (fileType) params.set("file_type", fileType);
    if (status) params.set("status", status);
    if (search) params.set("search", search);

    const token = getToken();
    setLoading(true);
    fetch(`${API_URL}/documents/?${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => {
        if (!r.ok) throw new Error("Ошибка загрузки");
        return r.json();
      })
      .then((data: DocsPage) => {
        setDocs(data.items);
        setTotal(data.total);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }

  const totalPages = Math.ceil(total / perPage);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Документы</h1>
      </div>

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="Поиск по имени файла..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="w-full max-w-md px-4 py-2.5 border border-gray-200 rounded-lg text-sm bg-white"
        />
      </div>

      {/* Type chips */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4">
        <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">Тип документа</h2>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => { setFileType(""); setPage(1); }}
            className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
              fileType === ""
                ? "bg-[#1B3A5C] text-white border-[#1B3A5C]"
                : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
            }`}
          >
            Все
          </button>
          {Object.entries(DOC_TYPE_LABELS).map(([key, label]) => (
            <button
              key={key}
              onClick={() => { setFileType(fileType === key ? "" : key); setPage(1); }}
              className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                fileType === key
                  ? "bg-[#1B3A5C] text-white border-[#1B3A5C]"
                  : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Status chips */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">Статус</h2>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => { setStatus(""); setPage(1); }}
            className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
              status === ""
                ? "bg-[#1B3A5C] text-white border-[#1B3A5C]"
                : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
            }`}
          >
            Все
          </button>
          {Object.entries(STATUS_STYLES).map(([key, { label }]) => (
            <button
              key={key}
              onClick={() => { setStatus(status === key ? "" : key); setPage(1); }}
              className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                status === key
                  ? "bg-[#1B3A5C] text-white border-[#1B3A5C]"
                  : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Documents table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-[#1B3A5C]">
              <th className="text-left px-4 py-3 text-xs font-medium text-white/60 uppercase tracking-wide">
                Файл
              </th>
              <th className="text-left px-4 py-3 text-xs font-medium text-white/60 uppercase tracking-wide">
                Тип
              </th>
              <th className="text-left px-4 py-3 text-xs font-medium text-white/60 uppercase tracking-wide">
                Дело
              </th>
              <th className="text-left px-4 py-3 text-xs font-medium text-white/60 uppercase tracking-wide">
                Клиент
              </th>
              <th className="text-left px-4 py-3 text-xs font-medium text-white/60 uppercase tracking-wide">
                Статус
              </th>
              <th className="text-left px-4 py-3 text-xs font-medium text-white/60 uppercase tracking-wide">
                Дата
              </th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 7 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 bg-gray-100 rounded animate-pulse w-3/4" />
                    </td>
                  ))}
                </tr>
              ))
            ) : docs.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-16 text-gray-400">
                  <p className="text-base">Документов не найдено</p>
                  {(fileType || status || search) && (
                    <p className="text-sm mt-1">Попробуйте изменить фильтры</p>
                  )}
                </td>
              </tr>
            ) : (
              docs.map((doc) => (
                <tr key={doc.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-gray-900 truncate max-w-[180px]" title={doc.file_name ?? ""}>
                      {doc.file_name || "—"}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {DOC_TYPE_LABELS[doc.document_type] ?? doc.document_type}
                  </td>
                  <td className="px-4 py-3">
                    <a
                      href={`/cases/${doc.case_id}`}
                      className="text-sm text-[#1B3A5C] hover:underline font-medium"
                    >
                      {doc.case_number || doc.case_id.slice(0, 8)}
                    </a>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {doc.client_name}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={doc.status} />
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {new Date(doc.created_at).toLocaleDateString("ru-RU")}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {doc.download_url ? (
                      <a
                        href={doc.download_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs px-3 py-1 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors"
                      >
                        Скачать
                      </a>
                    ) : (
                      <span className="text-xs text-gray-300">—</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {!loading && totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
            <p className="text-sm text-gray-500">
              {total} документов · страница {page} из {totalPages}
            </p>
            <div className="flex gap-1">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
                className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50 disabled:opacity-40"
              >
                ←
              </button>
              {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                const p = i + 1;
                return (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                      p === page
                        ? "bg-[#1B3A5C] text-white border-[#1B3A5C]"
                        : "border-gray-200 text-gray-500 hover:bg-gray-50"
                    }`}
                  >
                    {p}
                  </button>
                );
              })}
              <button
                disabled={page === totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50 disabled:opacity-40"
              >
                →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
