"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost, apiPatch } from "@/lib/api";
import { getUser } from "@/lib/auth";

interface Suggestion {
  id: string;
  title: string;
  body: string;
  status: string;
  admin_note?: string;
  author_id: string;
  author_name: string;
  created_at: string;
}

const STATUS_BADGE: Record<string, string> = {
  new: "bg-gray-100 text-gray-600",
  under_review: "bg-blue-100 text-blue-700",
  adopted: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-600",
};

const STATUS_LABELS: Record<string, string> = {
  new: "На рассмотрении",
  under_review: "Рассматривается",
  adopted: "Принята",
  rejected: "Отклонена",
};

const ADMIN_STATUS_OPTIONS = ["new", "under_review", "adopted", "rejected"];

const STATUS_FILTER_OPTIONS = [
  { value: "all", label: "Все" },
  { value: "new", label: "Новые" },
  { value: "under_review", label: "Рассматривается" },
  { value: "adopted", label: "Принятые" },
  { value: "rejected", label: "Отклонённые" },
];

export default function IdeasPage() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");

  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState(false);

  const [adminEdit, setAdminEdit] = useState<
    Record<string, { status: string; admin_note: string }>
  >({});
  const [savingId, setSavingId] = useState<string | null>(null);

  const user = getUser();
  const isAdminOrOps =
    user?.role === "admin" || user?.role === "operations_director";

  function fetchSuggestions() {
    const params = new URLSearchParams();
    if (statusFilter !== "all") params.set("status", statusFilter);
    setLoading(true);
    apiGet(`/staff/suggestions?${params.toString()}`)
      .then((d) => setSuggestions(Array.isArray(d) ? d : []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchSuggestions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !body.trim()) return;
    setSubmitting(true);
    setFormError(null);
    setFormSuccess(false);
    try {
      const created = await apiPost("/staff/suggestions", { title, body });
      if (created) {
        setSuggestions((prev) => [created, ...prev]);
        setTitle("");
        setBody("");
        setFormSuccess(true);
        setTimeout(() => setFormSuccess(false), 3000);
      }
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Ошибка отправки");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleAdminSave(id: string) {
    const edit = adminEdit[id];
    if (!edit) return;
    setSavingId(id);
    try {
      const updated = await apiPatch(`/staff/suggestions/${id}`, {
        status: edit.status,
        admin_note: edit.admin_note,
      });
      if (updated) {
        setSuggestions((prev) => prev.map((s) => (s.id === id ? updated : s)));
        setAdminEdit((prev) => {
          const next = { ...prev };
          delete next[id];
          return next;
        });
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSavingId(null);
    }
  }

  function initAdminEdit(s: Suggestion) {
    setAdminEdit((prev) => ({
      ...prev,
      [s.id]: { status: s.status, admin_note: s.admin_note || "" },
    }));
  }

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-[#1B3A5C] font-heading">
          Банк идей
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Предлагайте идеи по улучшению работы компании
        </p>
      </div>

      {/* Submit form */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 mb-8">
        <h2 className="text-base font-medium text-gray-900 mb-4">
          Предложить идею
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-500 mb-1.5">
              Заголовок
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Краткое название идеи"
              required
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-[#1B3A5C] bg-white transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-500 mb-1.5">
              Описание
            </label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Расскажите подробнее о своей идее..."
              required
              rows={4}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-[#1B3A5C] bg-white resize-none transition-colors"
            />
          </div>
          {formError && (
            <p className="text-sm text-red-500">{formError}</p>
          )}
          {formSuccess && (
            <p className="text-sm text-green-600">
              Идея отправлена успешно!
            </p>
          )}
          <button
            type="submit"
            disabled={submitting || !title.trim() || !body.trim()}
            className="px-4 py-2 text-sm bg-[#1B3A5C] text-white rounded-lg hover:bg-[#142d48] disabled:opacity-50 transition-colors"
          >
            {submitting ? "Отправка..." : "Отправить"}
          </button>
        </form>
      </div>

      {/* Filter */}
      <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-0.5 w-fit flex-wrap">
        {STATUS_FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setStatusFilter(opt.value)}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              statusFilter === opt.value
                ? "bg-white shadow-sm text-gray-900 font-medium"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* List */}
      {loading ? (
        <p className="text-gray-400 py-8 text-center">Загрузка...</p>
      ) : suggestions.length === 0 ? (
        <p className="text-gray-400 py-8 text-center">Идей пока нет</p>
      ) : (
        <div className="space-y-4">
          {suggestions.map((s) => {
            const edit = adminEdit[s.id];
            return (
              <div
                key={s.id}
                className="bg-white rounded-xl border border-gray-100 shadow-sm p-5"
              >
                <div className="flex items-start justify-between gap-3 mb-2">
                  <h3 className="text-base font-medium text-gray-900">
                    {s.title}
                  </h3>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium flex-shrink-0 ${
                      STATUS_BADGE[s.status] ?? "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {STATUS_LABELS[s.status] ?? s.status}
                  </span>
                </div>
                <p className="text-sm text-gray-500 mb-3 whitespace-pre-wrap">
                  {s.body.length > 200 ? s.body.slice(0, 200) + "…" : s.body}
                </p>
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <span>{s.author_name}</span>
                  <span>·</span>
                  <span>
                    {new Date(s.created_at).toLocaleDateString("ru-RU")}
                  </span>
                </div>

                {/* Admin note */}
                {s.admin_note && !edit && (
                  <div className="mt-3 p-3 bg-[#C9A84C]/10 rounded-lg border border-[#C9A84C]/30">
                    <p className="text-xs font-medium text-[#C9A84C] mb-1">
                      Примечание
                    </p>
                    <p className="text-sm text-gray-700 italic">{s.admin_note}</p>
                  </div>
                )}

                {/* Admin controls */}
                {isAdminOrOps && (
                  <div className="mt-4 border-t border-gray-50 pt-4">
                    {edit ? (
                      <div className="space-y-3">
                        <select
                          value={edit.status}
                          onChange={(e) =>
                            setAdminEdit((prev) => ({
                              ...prev,
                              [s.id]: { ...prev[s.id], status: e.target.value },
                            }))
                          }
                          className="px-2 py-1.5 text-sm border border-gray-200 rounded-lg bg-white"
                        >
                          {ADMIN_STATUS_OPTIONS.map((opt) => (
                            <option key={opt} value={opt}>
                              {STATUS_LABELS[opt]}
                            </option>
                          ))}
                        </select>
                        <textarea
                          value={edit.admin_note}
                          onChange={(e) =>
                            setAdminEdit((prev) => ({
                              ...prev,
                              [s.id]: {
                                ...prev[s.id],
                                admin_note: e.target.value,
                              },
                            }))
                          }
                          placeholder="Примечание (опционально)"
                          rows={2}
                          className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-[#1B3A5C] resize-none"
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleAdminSave(s.id)}
                            disabled={savingId === s.id}
                            className="px-3 py-1.5 text-xs bg-[#1B3A5C] text-white rounded-lg hover:bg-[#142d48] disabled:opacity-50"
                          >
                            {savingId === s.id ? "Сохранение..." : "Сохранить"}
                          </button>
                          <button
                            onClick={() =>
                              setAdminEdit((prev) => {
                                const next = { ...prev };
                                delete next[s.id];
                                return next;
                              })
                            }
                            className="px-3 py-1.5 text-xs border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50"
                          >
                            Отмена
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button
                        onClick={() => initAdminEdit(s)}
                        className="text-xs px-3 py-1.5 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50"
                      >
                        Рассмотреть
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
