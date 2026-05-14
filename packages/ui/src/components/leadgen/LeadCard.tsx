import Link from "next/link";
import { cn } from "@/lib/utils";
import { Lead } from "@/types/leadgen";
import { formatCurrency, formatRelative } from "@/lib/leadgen-utils";
import ChannelBadge from "./ChannelBadge";

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null)
    return <span className="text-xs text-text-muted">—</span>;

  const cls =
    score <= 40
      ? "bg-red-100 text-red-700"
      : score <= 70
        ? "bg-yellow-100 text-yellow-700"
        : "bg-green-100 text-green-700";

  return (
    <span className={cn("text-xs px-1.5 py-0.5 rounded-full font-semibold", cls)}>
      {score}
    </span>
  );
}

export default function LeadCard({ lead }: { lead: Lead }) {
  return (
    <Link href={`/leadgen/leads/${lead.id}`}>
      <div className="bg-white rounded-lg p-3 shadow-card hover:shadow-hover transition-shadow cursor-pointer border border-neutral group">
        <div className="flex items-start justify-between mb-2">
          <p className="text-sm font-medium text-text truncate mr-2 group-hover:text-primary transition-colors">
            {lead.name ?? "Без имени"}
          </p>
          <ScoreBadge score={lead.qualification_score} />
        </div>

        <div className="mb-2">
          <ChannelBadge channel={lead.channel} />
        </div>

        {lead.debt_amount !== null && (
          <p className="text-sm font-medium text-text-body mb-1">
            {formatCurrency(lead.debt_amount)}
          </p>
        )}

        {lead.last_message_at && (
          <p className="text-xs text-text-muted mt-1">
            {formatRelative(lead.last_message_at)}
          </p>
        )}
      </div>
    </Link>
  );
}
