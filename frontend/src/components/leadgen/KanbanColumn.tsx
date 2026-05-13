import { Lead } from "@/types/leadgen";
import LeadCard from "./LeadCard";

interface KanbanColumnProps {
  title: string;
  leads: Lead[];
  isLoading?: boolean;
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-lg p-3 border border-neutral animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
      <div className="h-3 bg-gray-100 rounded w-1/2 mb-2" />
      <div className="h-3 bg-gray-100 rounded w-2/3" />
    </div>
  );
}

export default function KanbanColumn({
  title,
  leads,
  isLoading = false,
}: KanbanColumnProps) {
  return (
    <div className="flex flex-col min-w-[220px] w-[220px] flex-shrink-0">
      <div
        className="flex items-center justify-between px-3 py-2 rounded-t-lg mb-2"
        style={{ background: "#1B3A5C" }}
      >
        <h3
          className="text-sm font-semibold text-white"
          style={{ fontFamily: "Georgia, serif" }}
        >
          {title}
        </h3>
        <span className="text-xs font-medium text-white bg-white/20 rounded-full px-2 py-0.5">
          {isLoading ? "…" : leads.length}
        </span>
      </div>

      <div className="flex flex-col gap-2 min-h-[120px]">
        {isLoading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : leads.length === 0 ? (
          <div className="flex items-center justify-center h-24 rounded-lg border-2 border-dashed border-neutral">
            <p className="text-xs text-text-muted">Нет лидов</p>
          </div>
        ) : (
          leads.map((lead) => <LeadCard key={lead.id} lead={lead} />)
        )}
      </div>
    </div>
  );
}
