"use client";

import { useState, useEffect } from "react";
import LeadKanban from "@/components/leads/LeadKanban";
import { getLeads, Lead } from "@/lib/api";

const STUB_LEADS: Lead[] = [
  { id: "1", full_name: "Иванов Сергей", phone: "+7 900 123-45-67", channel: "telegram", score: 82, funnel_stage: "incoming", created_at: new Date().toISOString(), status: "new" },
  { id: "2", full_name: "Петрова Мария", phone: "+7 911 234-56-78", channel: "website", score: 65, funnel_stage: "contacted", created_at: new Date().toISOString(), status: "new" },
  { id: "3", full_name: "Сидоров Алексей", phone: "+7 922 345-67-89", channel: "vk", score: 91, funnel_stage: "qualifying", created_at: new Date().toISOString(), status: "qualifying" },
  { id: "4", full_name: "Козлова Наталья", phone: "+7 933 456-78-90", channel: "phone", score: 78, funnel_stage: "hot", created_at: new Date().toISOString(), status: "qualifying" },
  { id: "5", full_name: "Морозов Дмитрий", phone: "+7 944 567-89-01", channel: "telegram", score: 95, funnel_stage: "ready_to_convert", created_at: new Date().toISOString(), status: "qualified" },
];

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [usingStub, setUsingStub] = useState(false);

  useEffect(() => {
    getLeads()
      .then(data => { setLeads(data); setLoading(false); })
      .catch(() => { setLeads(STUB_LEADS); setUsingStub(true); setLoading(false); });
  }, []);

  if (loading) return <div className="p-8 text-center text-text-muted">Загрузка...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-primary font-heading">Лиды</h1>
          <p className="text-sm text-text-muted mt-1">Воронка квалификации</p>
        </div>
        {usingStub && (
          <div className="text-xs px-3 py-1 bg-warning/10 border border-warning text-warning rounded-lg">
            API недоступен — показаны тестовые данные
          </div>
        )}
      </div>
      <LeadKanban leads={leads} />
    </div>
  );
}
