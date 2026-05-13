"use client";

import { useState } from "react";
import { Lead } from "@/types/leadgen";
import { formatCurrency, FUNNEL_STAGE_LABELS, STATUS_LABELS, API_BASE } from "@/lib/leadgen-utils";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import ChannelBadge from "./ChannelBadge";
import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<string, string> = {
  new: "bg-blue-100 text-blue-700",
  in_progress: "bg-yellow-100 text-yellow-700",
  qualified: "bg-green-100 text-green-700",
  disqualified: "bg-gray-100 text-gray-600",
  converted: "bg-purple-100 text-purple-700",
  spam: "bg-red-100 text-red-700",
};

interface LeadDataPanelProps {
  lead: Lead;
  onUpdate: (updated: Lead) => void;
  onSpam: () => void;
  onConvert: () => void;
  showToast: (msg: string, type?: "success" | "error") => void;
}

export default function LeadDataPanel({
  lead,
  onUpdate,
  onSpam,
  onConvert,
  showToast,
}: LeadDataPanelProps) {
  const [qualifying, setQualifying] = useState(false);
  const [updatingStage, setUpdatingStage] = useState(false);
  const [spamming, setSpamming] = useState(false);

  async function handleQualify() {
    setQualifying(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/leads/${lead.id}/qualify`, {
        method: "POST",
      });
      if (!res.ok) throw new Error();
      const updated: Lead = await res.json();
      onUpdate(updated);
      showToast("Квалификация завершена", "success");
    } catch {
      showToast("Ошибка квалификации", "error");
    } finally {
      setQualifying(false);
    }
  }

  async function handleStageChange(stage: string) {
    setUpdatingStage(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/leads/${lead.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ funnel_stage: stage }),
      });
      if (!res.ok) throw new Error();
      const updated: Lead = await res.json();
      onUpdate(updated);
      showToast("Стадия обновлена", "success");
    } catch {
      showToast("Ошибка обновления", "error");
    } finally {
      setUpdatingStage(false);
    }
  }

  async function handleSpam() {
    if (!confirm("Пометить лид как спам?")) return;
    setSpamming(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/leads/${lead.id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error();
      onSpam();
    } catch {
      showToast("Ошибка", "error");
      setSpamming(false);
    }
  }

  const scoreColor =
    lead.qualification_score === null
      ? "#6B7280"
      : lead.qualification_score <= 40
        ? "#E24B4A"
        : lead.qualification_score <= 70
          ? "#BA7517"
          : "#1D9E75";

  return (
    <div className="flex flex-col gap-4 h-full overflow-y-auto">
      {/* Контакт */}
      <section className="bg-white rounded-xl p-4 shadow-card">
        <h3
          className="text-sm font-semibold mb-3"
          style={{ color: "#1B3A5C", fontFamily: "Georgia, serif" }}
        >
          Контакт
        </h3>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-text-muted">Имя</dt>
            <dd className="font-medium">{lead.name ?? "—"}</dd>
          </div>
          {lead.phone && (
            <div className="flex justify-between">
              <dt className="text-text-muted">Телефон</dt>
              <dd>{lead.phone}</dd>
            </div>
          )}
          {lead.email && (
            <div className="flex justify-between">
              <dt className="text-text-muted">Email</dt>
              <dd>{lead.email}</dd>
            </div>
          )}
          <div className="flex justify-between items-center">
            <dt className="text-text-muted">Канал</dt>
            <dd>
              <ChannelBadge channel={lead.channel} />
            </dd>
          </div>
          <div className="flex justify-between items-center">
            <dt className="text-text-muted">Статус</dt>
            <dd>
              <span
                className={cn(
                  "text-xs px-2 py-0.5 rounded-full font-medium",
                  STATUS_STYLES[lead.status] ?? "bg-gray-100 text-gray-600"
                )}
              >
                {STATUS_LABELS[lead.status] ?? lead.status}
              </span>
            </dd>
          </div>
        </dl>
      </section>

      {/* Долг */}
      <section className="bg-white rounded-xl p-4 shadow-card">
        <h3
          className="text-sm font-semibold mb-3"
          style={{ color: "#1B3A5C", fontFamily: "Georgia, serif" }}
        >
          Долг
        </h3>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between items-center">
            <dt className="text-text-muted">Сумма</dt>
            <dd className="font-medium">
              {lead.debt_amount !== null
                ? formatCurrency(lead.debt_amount)
                : "—"}
            </dd>
          </div>
          {lead.debt_type && (
            <div className="flex justify-between">
              <dt className="text-text-muted">Тип</dt>
              <dd>{lead.debt_type}</dd>
            </div>
          )}
          <div className="flex justify-between">
            <dt className="text-text-muted">Имущество</dt>
            <dd>
              {lead.has_property === null
                ? "—"
                : lead.has_property
                  ? "Да"
                  : "Нет"}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-text-muted">Доход</dt>
            <dd>
              {lead.has_income === null ? "—" : lead.has_income ? "Да" : "Нет"}
            </dd>
          </div>
        </dl>
      </section>

      {/* AI Квалификация */}
      <section className="bg-white rounded-xl p-4 shadow-card">
        <h3
          className="text-sm font-semibold mb-3"
          style={{ color: "#1B3A5C", fontFamily: "Georgia, serif" }}
        >
          AI Квалификация
        </h3>
        <div className="flex items-center gap-3 mb-3">
          <span
            className="text-5xl font-bold font-heading leading-none"
            style={{ color: scoreColor }}
          >
            {lead.qualification_score ?? "—"}
          </span>
          <span className="text-xs text-text-muted">/ 100</span>
        </div>
        {lead.qualification_reasoning && (
          <p className="text-xs text-text-muted italic mb-3 leading-relaxed">
            {lead.qualification_reasoning}
          </p>
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={handleQualify}
          disabled={qualifying}
          className="w-full text-xs"
          style={
            qualifying
              ? {}
              : { borderColor: "#C9A84C", color: "#C9A84C" }
          }
        >
          {qualifying ? (
            <span className="flex items-center gap-2">
              <span className="w-3 h-3 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin" />
              Анализируем...
            </span>
          ) : (
            "Запустить квалификацию"
          )}
        </Button>
      </section>

      {/* Действия */}
      <section className="bg-white rounded-xl p-4 shadow-card">
        <h3
          className="text-sm font-semibold mb-3"
          style={{ color: "#1B3A5C", fontFamily: "Georgia, serif" }}
        >
          Действия
        </h3>
        <div className="space-y-3">
          <div>
            <p className="text-xs text-text-muted mb-1">Переместить в воронке</p>
            <Select
              defaultValue={lead.funnel_stage}
              onValueChange={handleStageChange}
              disabled={updatingStage}
            >
              <SelectTrigger className="text-sm h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(FUNNEL_STAGE_LABELS).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleSpam}
            disabled={spamming}
            className="w-full text-xs text-text-muted"
          >
            {spamming ? "Помечаем..." : "Пометить спамом"}
          </Button>

          <Button
            size="sm"
            onClick={onConvert}
            disabled={lead.status !== "qualified"}
            className="w-full text-xs font-semibold"
            style={
              lead.status === "qualified"
                ? { background: "#C9A84C", color: "#fff" }
                : {}
            }
          >
            Конвертировать в клиента
          </Button>
        </div>
      </section>
    </div>
  );
}
