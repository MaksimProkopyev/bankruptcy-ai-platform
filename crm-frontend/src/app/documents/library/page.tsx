"use client";

import { useEffect, useRef, useState } from "react";
import { auth } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DocumentMeta {
  key: string;
  name: string;
  category: string;
  client_scope: string;
  access_level: string;
  size_bytes: number;
  last_modified: string;
  tags: string[];
}

// ---------------------------------------------------------------------------
// Label maps
// ---------------------------------------------------------------------------

const CATEGORY_LABELS: Record<string, string> = {
  "": "Все",
  template: "Шаблоны",
  rag: "RAG",
  sop: "Регламенты",
};

const SCOPE_LABELS: Record<string, string> = {
  "": "Все",
  individual: "Физлица",
  sole_proprietor: "ИП",
  legal_entity: "Юрлица",
  credit_organization: "Кредитные орг.",
  all: "Все типы",
};

const CATEGORY_BADGE: Record<string, string> = {
  template: "bg-blue-100 text-blue-700",
  rag: "bg-purple-100 text-purple-700",
  sop: "bg-green-100 text-green-700",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("token") || "";
}

function getUserPermissions(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const token = getToken();
    if (!token) return [];
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.permissions || [];
  } catch {
    return [];
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} КБ`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Ошибка запроса" }));
    throw new Error(err.detail || "Ошибка запроса");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Upload modal
// ---------------------------------------------------------------------------

function UploadModal({
  onClose,
  onUploaded,
}: {
  onClose: () => void;
  onUploaded: (doc: DocumentMeta) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [category, setCategory] = useState("template");
  const [clientScope, setClientScope] = useState("all");
  const [accessLevel, setAccessLevel] = useState("internal");
  const [tags, setTags] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dropRef = useRef<HTMLDivElement>(null);

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const key = `uploads/${category}/${file.name}`;
      const params = new URLSearchParams({
        category,
        client_scope: clientScope,
        access_level: accessLevel,
        tags,
      });
      const form = new FormData();
      form.append("file", file);
      const doc = await apiFetch<DocumentMeta>(
        `/storage/documents/${encodeURIComponent(key)}?${params}`,
        { method: "POST", body: form }
      );
      onUploaded(doc);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ошибка загрузки");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-gray-900">Загрузить документ</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Drop zone */}
          <div
            ref={dropRef}
            onDrop={onDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => document.getElementById("lib-file-input")?.click()}
            className="border-2 border-dashed border-gray-200 rounded-lg p-6 text-center cursor-pointer hover:border-gray-400 transition-colors"
          >
            {file ? (
              <p className="text-sm text-gray-700 font-medium">{file.name}</p>
            ) : (
              <p className="text-sm text-gray-400">Перетащите файл или нажмите для выбора</p>
            )}
          </div>
          <input
            id="lib-file-input"
            type="file"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Категория</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg bg-white"
              >
                <option value="template">Шаблоны</option>
                <option value="rag">RAG</option>
                <option value="sop">Регламенты</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Тип клиента</label>
              <select
                value={clientScope}
                onChange={(e) => setClientScope(e.target.value)}
                className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg bg-white"
              >
                <option value="all">Все</option>
                <option value="individual">Физлица</option>
                <option value="sole_proprietor">ИП</option>
                <option value="legal_entity">Юрлица</option>
                <option value="credit_organization">Кредитные орг.</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Доступ</label>
              <select
                value={accessLevel}
                onChange={(e) => setAccessLevel(e.target.value)}
                className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg bg-white"
              >
                <option value="internal">Внутренний</option>
                <option value="public">Публичный</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Теги (через запятую)</label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="банкротство, суд"
                className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-lg"
              />
            </div>
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={uploading || !file}
              className="px-4 py-2 text-sm bg-[#1B3A5C] text-white rounded-lg hover:bg-[#142d48] disabled:opacity-50"
            >
              {uploading ? "Загрузка..." : "Загрузить"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function LibraryPage() {
  const [docs, setDocs] = useState<DocumentMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("");
  const [clientScope, setClientScope] = useState("");
  const [search, setSearch] = useState("");
  const [downloading, setDownloading] = useState<string | null>(null);
  const [deletingKey, setDeletingKey] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);

  const canWrite = getUserPermissions().includes("storage:write");

  function fetchDocs() {
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (clientScope) params.set("client_scope", clientScope);
    if (search) params.set("search", search);
    setLoading(true);
    apiFetch<DocumentMeta[]>(`/storage/documents?${params}`)
      .then(setDocs)
      .catch(console.error)
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchDocs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category, clientScope, search]);

  async function handleDownload(key: string) {
    setDownloading(key);
    try {
      const { url } = await apiFetch<{ url: string; expires_at: string }>(
        `/storage/documents/${encodeURIComponent(key)}/url`
      );
      window.open(url, "_blank");
    } catch (e) {
      console.error(e);
    } finally {
      setDownloading(null);
    }
  }

  async function handleDelete(key: string) {
    if (!confirm(`Удалить «${key.split("/").pop()}»?`)) return;
    setDeletingKey(key);
    try {
      await apiFetch(`/storage/documents/${encodeURIComponent(key)}`, { method: "DELETE" });
      setDocs((prev) => prev.filter((d) => d.key !== key));
    } catch (e) {
      console.error(e);
    } finally {
      setDeletingKey(null);
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Библиотека документов</h1>
          <p className="text-sm text-gray-500 mt-1">
            {docs.length} {docs.length === 1 ? "документ" : "документов"}
          </p>
        </div>
        {canWrite && (
          <button
            onClick={() => setShowUpload(true)}
            className="px-4 py-2 text-sm bg-[#1B3A5C] text-white rounded-lg hover:bg-[#142d48] transition-colors"
          >
            + Загрузить
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white text-gray-700"
        >
          {Object.entries(CATEGORY_LABELS).map(([val, label]) => (
            <option key={val} value={val}>{label}</option>
          ))}
        </select>

        <select
          value={clientScope}
          onChange={(e) => setClientScope(e.target.value)}
          className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white text-gray-700"
        >
          {Object.entries(SCOPE_LABELS)
            .filter(([val]) => val !== "all")
            .map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
        </select>

        <input
          type="text"
          placeholder="Поиск по названию..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white flex-1 min-w-[180px]"
        />
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-[#1B3A5C]">
              <th className="text-left px-4 py-3 text-xs font-medium text-white/60 uppercase tracking-wide">
                Название
              </th>
              <th className="text-left px-4 py-3 text-xs font-medium text-white/60 uppercase tracking-wide">
                Категория
              </th>
              <th className="text-left px-4 py-3 text-xs font-medium text-white/60 uppercase tracking-wide">
                Тип клиента
              </th>
              <th className="text-left px-4 py-3 text-xs font-medium text-white/60 uppercase tracking-wide">
                Размер
              </th>
              <th className="text-left px-4 py-3 text-xs font-medium text-white/60 uppercase tracking-wide">
                Дата
              </th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {loading ? (
              // Skeleton rows
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 6 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 bg-gray-100 rounded animate-pulse w-3/4" />
                    </td>
                  ))}
                </tr>
              ))
            ) : docs.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-16 text-gray-400">
                  <p className="text-base">Документов не найдено</p>
                  {(category || clientScope || search) && (
                    <p className="text-sm mt-1">Попробуйте изменить фильтры</p>
                  )}
                </td>
              </tr>
            ) : (
              docs.map((doc) => (
                <tr key={doc.key} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-gray-900 truncate max-w-xs" title={doc.name}>
                      {doc.name}
                    </p>
                    {doc.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {doc.tags.slice(0, 3).map((tag) => (
                          <span key={tag} className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        CATEGORY_BADGE[doc.category] ?? "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {CATEGORY_LABELS[doc.category] ?? doc.category}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {SCOPE_LABELS[doc.client_scope] ?? doc.client_scope}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {formatBytes(doc.size_bytes)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {new Date(doc.last_modified).toLocaleDateString("ru-RU")}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        disabled={downloading === doc.key}
                        onClick={() => handleDownload(doc.key)}
                        className="text-xs px-3 py-1 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors disabled:opacity-50"
                      >
                        {downloading === doc.key ? "..." : "Скачать"}
                      </button>
                      {canWrite && (
                        <button
                          disabled={deletingKey === doc.key}
                          onClick={() => handleDelete(doc.key)}
                          className="text-xs px-2 py-1 rounded-lg border border-red-100 text-red-400 hover:bg-red-50 hover:text-red-600 transition-colors disabled:opacity-50"
                          title="Удалить"
                        >
                          {deletingKey === doc.key ? "..." : "✕"}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onUploaded={(doc) => setDocs((prev) => [doc, ...prev])}
        />
      )}
    </div>
  );
}
