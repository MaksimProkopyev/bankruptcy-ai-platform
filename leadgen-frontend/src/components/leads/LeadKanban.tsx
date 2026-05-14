import { Lead } from "@/lib/api";
import LeadCard from "./LeadCard";

const COLUMNS: { stage: string; label: string }[] = [
  { stage: "incoming", label: "Входящие" },
  { stage: "contacted", label: "Контакт" },
  { stage: "qualifying", label: "Квалификация" },
  { stage: "hot", label: "Горячие" },
  { stage: "ready_to_convert", label: "К переводу" },
];

interface Props {
  leads: Lead[];
}

export default function LeadKanban({ leads }: Props) {
  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {COLUMNS.map(({ stage, label }) => {
        const col = leads.filter(l => l.funnel_stage === stage);
        return (
          <div key={stage} className="w-56 shrink-0">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-semibold text-text">{label}</span>
              <span className="text-xs bg-surface text-text-muted px-2 py-0.5 rounded-full">{col.length}</span>
            </div>
            <div className="space-y-2 min-h-[120px]">
              {col.map(lead => (
                <LeadCard key={lead.id} lead={lead} />
              ))}
              {col.length === 0 && (
                <div className="border-2 border-dashed border-neutral rounded-lg p-4 text-center text-xs text-text-muted">
                  Пусто
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
