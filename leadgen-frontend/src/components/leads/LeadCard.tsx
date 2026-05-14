import { Lead } from "@/lib/api";
import Link from "next/link";

const CHANNEL_ICONS: Record<string, string> = {
  telegram: "✈️",
  vk: "🔵",
  website: "🌐",
  phone: "📞",
  email: "📧",
};

interface Props {
  lead: Lead;
}

export default function LeadCard({ lead }: Props) {
  const scoreColor =
    lead.score >= 80 ? "bg-success/15 text-success" :
    lead.score >= 60 ? "bg-warning/15 text-warning" :
    "bg-danger/15 text-danger";

  const date = new Date(lead.created_at).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "short",
  });

  return (
    <Link href={`/leads/${lead.id}`}>
      <div className="bg-white rounded-lg border border-neutral p-3 shadow-card hover:shadow-hover transition-shadow cursor-pointer space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="text-base">{CHANNEL_ICONS[lead.channel] || "📄"}</span>
            <span className="text-sm font-medium text-text truncate">{lead.full_name || "Без имени"}</span>
          </div>
          <span className={`shrink-0 text-xs font-bold px-1.5 py-0.5 rounded-full ${scoreColor}`}>
            {lead.score}
          </span>
        </div>
        <div className="text-xs text-text-muted">{date}</div>
      </div>
    </Link>
  );
}
