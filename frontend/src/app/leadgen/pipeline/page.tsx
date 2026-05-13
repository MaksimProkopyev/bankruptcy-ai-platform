"use client";

import { useState, useEffect, useCallback } from "react";
import { Lead, FunnelStage } from "@/types/leadgen";
import { API_BASE, FUNNEL_STAGE_LABELS } from "@/lib/leadgen-utils";
import KanbanColumn from "@/components/leadgen/KanbanColumn";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";

const STAGES: FunnelStage[] = [
  "incoming",
  "contacted",
  "qualifying",
  "hot",
  "ready_to_convert",
];

type ColumnData = Record<FunnelStage, Lead[]>;
type LoadingState = Record<FunnelStage, boolean>;

export default function PipelinePage() {
  const [columns, setColumns] = useState<ColumnData>({
    incoming: [],
    contacted: [],
    qualifying: [],
    hot: [],
    ready_to_convert: [],
  });
  const [loading, setLoading] = useState<LoadingState>({
    incoming: true,
    contacted: true,
    qualifying: true,
    hot: true,
    ready_to_convert: true,
  });
  const [refreshing, setRefreshing] = useState(false);

  const fetchStage = useCallback(async (stage: FunnelStage) => {
    setLoading((prev) => ({ ...prev, [stage]: true }));
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/leads?funnel_stage=${stage}&limit=50`
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const items: Lead[] = Array.isArray(data)
        ? data
        : data.items ?? data.leads ?? [];
      setColumns((prev) => ({ ...prev, [stage]: items }));
    } catch {
      setColumns((prev) => ({ ...prev, [stage]: [] }));
    } finally {
      setLoading((prev) => ({ ...prev, [stage]: false }));
    }
  }, []);

  const fetchAll = useCallback(async () => {
    await Promise.all(STAGES.map(fetchStage));
  }, [fetchStage]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  async function handleRefresh() {
    setRefreshing(true);
    await fetchAll();
    setRefreshing(false);
  }

  const totalCount = STAGES.reduce((sum, s) => sum + columns[s].length, 0);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-shrink-0">
        <div>
          <h1
            className="text-2xl font-bold"
            style={{ fontFamily: "Georgia, serif", color: "#1B3A5C" }}
          >
            Воронка лидов
          </h1>
          <p className="text-sm text-text-muted mt-0.5">
            Всего лидов: {totalCount}
          </p>
        </div>
        <Button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 text-sm font-semibold"
          style={{ background: "#C9A84C", color: "#fff" }}
        >
          <RefreshCw
            className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`}
          />
          Обновить
        </Button>
      </div>

      {/* Kanban board */}
      <div className="flex gap-4 overflow-x-auto pb-4 flex-1">
        {STAGES.map((stage) => (
          <KanbanColumn
            key={stage}
            title={FUNNEL_STAGE_LABELS[stage]}
            leads={columns[stage]}
            isLoading={loading[stage]}
          />
        ))}
      </div>
    </div>
  );
}
