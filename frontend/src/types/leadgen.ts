export type Channel =
  | "telegram"
  | "whatsapp"
  | "vk"
  | "email"
  | "ok"
  | "facebook"
  | "avito"
  | "callback"
  | "web"
  | "max";

export type LeadStatus =
  | "new"
  | "in_progress"
  | "qualified"
  | "disqualified"
  | "converted"
  | "spam";

export type FunnelStage =
  | "incoming"
  | "contacted"
  | "qualifying"
  | "hot"
  | "ready_to_convert";

export type MessageDirection = "inbound" | "outbound";

export interface Lead {
  id: string;
  name: string | null;
  channel: Channel;
  phone: string | null;
  email: string | null;
  debt_amount: number | null;
  debt_type: string | null;
  has_property: boolean | null;
  has_income: boolean | null;
  status: LeadStatus;
  funnel_stage: FunnelStage;
  qualification_score: number | null;
  qualification_reasoning: string | null;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  lead_id: string;
  direction: MessageDirection;
  content: string;
  channel: Channel;
  sent_at: string;
}

export interface Prospect {
  id: string;
  lead_id: string;
  status: "pending" | "confirmed" | "rejected";
  qualification_data: {
    name?: string;
    debt_amount?: number;
    channel?: Channel;
    score?: number;
  };
  created_at: string;
}

export interface ChannelStat {
  channel: Channel;
  count: number;
}

export interface ActivityRow {
  date: string;
  new_leads: number;
  qualified: number;
  converted: number;
}

export interface FunnelStats {
  all: number;
  contacted: number;
  qualifying: number;
  ready: number;
  converted: number;
}

export interface Stats {
  leads_today: number;
  leads_qualified: number;
  leads_converted: number;
  avg_score: number;
  by_channel: ChannelStat[];
  funnel: FunnelStats;
  activity: ActivityRow[];
}

export interface LeadsResponse {
  items: Lead[];
  total: number;
}

export interface MessagesResponse {
  items: Message[];
}

export interface ProspectsResponse {
  items: Prospect[];
}
