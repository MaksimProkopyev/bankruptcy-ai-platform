"use client";

import { useState, useEffect, useCallback } from "react";
import { Prospect } from "@/types/leadgen";
import { API_BASE } from "@/lib/leadgen-utils";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import ProspectRow from "@/components/leadgen/ProspectRow";

interface Toast {
  id: number;
  message: string;
  type: "success" | "error";
}

let toastId = 0;

export default function ProspectsPage() {
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [loading, setLoading] = useState(true);
  const [toasts, setToasts] = useState<Toast[]>([]);

  function showToast(message: string, type: "success" | "error" = "success") {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }

  const fetchProspects = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/prospects?status=pending&limit=100`
      );
      if (!res.ok) throw new Error();
      const data = await res.json();
      const items: Prospect[] = Array.isArray(data)
        ? data
        : data.items ?? data.prospects ?? [];
      setProspects(items);
    } catch {
      setProspects([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProspects();
  }, [fetchProspects]);

  async function handleConfirm(id: string) {
    const res = await fetch(`${API_BASE}/api/v1/prospects/${id}/confirm`, {
      method: "POST",
    });
    if (res.ok) {
      setProspects((prev) => prev.filter((p) => p.id !== id));
      showToast("Клиент создан в CRM", "success");
    } else {
      showToast("Ошибка создания клиента", "error");
      throw new Error();
    }
  }

  async function handleReject(id: string) {
    const res = await fetch(`${API_BASE}/api/v1/prospects/${id}/reject`, {
      method: "POST",
    });
    if (res.ok) {
      setProspects((prev) => prev.filter((p) => p.id !== id));
      showToast("Лид возвращён в воронку", "success");
    } else {
      showToast("Ошибка отклонения", "error");
      throw new Error();
    }
  }

  return (
    <div className="relative">
      {/* Toast notifications */}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="px-4 py-3 rounded-lg shadow-hover text-sm font-medium text-white animate-in fade-in slide-in-from-top-2"
            style={{
              background: t.type === "success" ? "#1D9E75" : "#E24B4A",
              minWidth: "240px",
            }}
          >
            {t.message}
          </div>
        ))}
      </div>

      {/* Header */}
      <div className="mb-6">
        <h1
          className="text-2xl font-bold"
          style={{ fontFamily: "Georgia, serif", color: "#1B3A5C" }}
        >
          Prospects
        </h1>
        <p className="text-sm text-text-muted mt-0.5">
          Лиды на подтверждении конвертации
        </p>
      </div>

      {/* Content */}
      {loading ? (
        <div className="bg-white rounded-xl shadow-card p-8">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="flex gap-4 py-3 border-b border-neutral last:border-0 animate-pulse"
            >
              <div className="h-4 bg-gray-200 rounded flex-1" />
              <div className="h-4 bg-gray-100 rounded w-24" />
              <div className="h-4 bg-gray-100 rounded w-20" />
              <div className="h-4 bg-gray-100 rounded w-16" />
            </div>
          ))}
        </div>
      ) : prospects.length === 0 ? (
        <div className="bg-white rounded-xl shadow-card p-16 flex flex-col items-center gap-4">
          <div className="text-6xl">📋</div>
          <p
            className="text-lg font-semibold"
            style={{ color: "#1B3A5C", fontFamily: "Georgia, serif" }}
          >
            Нет лидов на подтверждении
          </p>
          <p className="text-sm text-text-muted">
            Когда лиды будут квалифицированы — они появятся здесь
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow style={{ background: "#F8F7F4" }}>
                <TableHead className="font-semibold text-text">Имя</TableHead>
                <TableHead className="font-semibold text-text">Канал</TableHead>
                <TableHead className="font-semibold text-text">Долг</TableHead>
                <TableHead className="font-semibold text-text">Score</TableHead>
                <TableHead className="font-semibold text-text">Дата</TableHead>
                <TableHead className="font-semibold text-text">
                  Действия
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {prospects.map((prospect) => (
                <ProspectRow
                  key={prospect.id}
                  prospect={prospect}
                  onConfirm={handleConfirm}
                  onReject={handleReject}
                />
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
