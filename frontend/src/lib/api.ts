/**
 * API client — typed fetch wrapper with auth.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type Method = "GET" | "POST" | "PATCH" | "DELETE";

function getCookieValue(name: string): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : "";
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(method: Method, path: string, body?: unknown): Promise<T> {
  // Try localStorage first, then cookies
  let token: string | null = null;
  if (typeof window !== "undefined") {
    token = localStorage.getItem("token") || getCookieValue("staff_token") || null;
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    if (res.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("token");
      document.cookie = "staff_token=; path=/; max-age=0";
      window.location.href = "/crm/login";
    }
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new ApiError(res.status, err.detail || "Request failed");
  }

  return res.json();
}

// ---- Auth ----
export const auth = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>("POST", "/auth/login", { email, password }),
  me: () => request<User>("GET", "/auth/me"),
  seedAdmin: () => request<User>("POST", "/auth/seed-admin"),
};

// ---- Cases ----
export const cases = {
  list: (params?: { status?: string; page?: number }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.page) q.set("page", String(params.page));
    return request<Case[]>("GET", `/cases/?${q}`);
  },
  get: (id: string) => request<CaseDetail>("GET", `/cases/${id}`),
  create: (data: CaseCreate) => request<Case>("POST", "/cases/", data),
  update: (id: string, data: Partial<CaseUpdate>) =>
    request<Case>("PATCH", `/cases/${id}`, data),
  timeline: (id: string) => request<CaseEvent[]>("GET", `/cases/${id}/timeline`),
  addCreditor: (caseId: string, data: CreditorCreate) =>
    request<Creditor>("POST", `/cases/${caseId}/creditors`, data),
  addDeadline: (caseId: string, data: DeadlineCreate) =>
    request<Deadline>("POST", `/cases/${caseId}/deadlines`, data),
};

// ---- Clients ----
export const clients = {
  list: (params?: { search?: string; page?: number }) => {
    const q = new URLSearchParams();
    if (params?.search) q.set("search", params.search);
    if (params?.page) q.set("page", String(params.page));
    return request<Client[]>("GET", `/clients/?${q}`);
  },
  get: (id: string) => request<Client>("GET", `/clients/${id}`),
  create: (data: ClientCreate) => request<Client>("POST", "/clients/", data),
};

// ---- AI ----
export const ai = {
  qualify: (data: QualificationInput) =>
    request<QualificationResult>("POST", "/ai/qualify", data),
};

// ---- Analytics ----
export const analytics = {
  summary: () => request<DashboardSummary>("GET", "/analytics/summary"),
  funnel: () => request<FunnelRow[]>("GET", "/analytics/funnel"),
  lawyerWorkload: () => request<LawyerWorkload[]>("GET", "/analytics/lawyer-workload"),
};

// ---- Types ----

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  is_active: boolean;
}

export interface Client {
  id: string;
  first_name: string;
  last_name: string;
  patronymic?: string;
  phone: string;
  email?: string;
  region?: string;
  lead_source?: string;
  created_at: string;
}

export interface ClientCreate {
  first_name: string;
  last_name: string;
  phone: string;
  email?: string;
  region?: string;
  lead_source?: string;
}

export interface Case {
  id: string;
  case_number?: string;
  client_id: string;
  assigned_lawyer_id?: string;
  status: string;
  procedure_type: string;
  total_debt?: number;
  ai_score?: number;
  ai_risk_level?: string;
  service_fee?: number;
  created_at: string;
  updated_at: string;
}

export interface CaseDetail extends Case {
  court_name?: string;
  filing_date?: string;
  client?: Client;
  lawyer?: User;
  creditors: Creditor[];
  documents: Document[];
  deadlines: Deadline[];
  recent_events: CaseEvent[];
}

export interface CaseCreate {
  client_id: string;
  total_debt?: number;
  notes?: string;
}

export interface CaseUpdate {
  status?: string;
  assigned_lawyer_id?: string;
  notes?: string;
}

export interface Creditor {
  id: string;
  name: string;
  creditor_type: string;
  total_amount: number;
  included_in_registry: boolean;
  is_secured: boolean;
}

export interface CreditorCreate {
  name: string;
  creditor_type: string;
  total_amount: number;
}

export interface Document {
  id: string;
  document_type: string;
  status: string;
  file_name?: string;
  ai_confidence?: number;
  created_at: string;
}

export interface Deadline {
  id: string;
  title: string;
  due_date: string;
  priority: string;
  status: string;
}

export interface DeadlineCreate {
  title: string;
  due_date: string;
  priority?: string;
}

export interface CaseEvent {
  id: string;
  event_type: string;
  title: string;
  description?: string;
  created_at: string;
}

export interface QualificationInput {
  total_debt: number;
  creditors_count: number;
  creditor_types: string[];
  monthly_income?: number;
  is_employed: boolean;
  has_property: boolean;
  property_types?: string[];
  has_transactions_3y: boolean;
  marital_status: string;
  has_enforcement_proceedings: boolean;
}

export interface QualificationResult {
  is_eligible: boolean;
  recommended_procedure: string;
  procedure_type?: string;
  estimated_cost_min: number;
  estimated_cost_max: number;
  estimated_duration_months_min: number;
  estimated_duration_months_max: number;
  risk_level: string;
  risk_factors: string[];
  confidence: number;
  explanation: string;
  needs_lawyer_review: boolean;
}

export interface DashboardSummary {
  total_cases: number;
  active_cases: number;
  total_revenue: number;
}

export interface FunnelRow {
  month: string;
  total_leads: number;
  qualified: number;
  consultations: number;
  contracts: number;
  filed: number;
  completed: number;
}

export interface LawyerWorkload {
  lawyer_id: string;
  lawyer_name: string;
  total_cases: number;
  active_court_cases: number;
  completed_cases: number;
}

// Staff API helpers (used by (staff) pages)
import { getCookie } from "./auth";

function getStaffHeaders(): Record<string, string> {
  const token = getCookie("staff_token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function handleStaffResponse(res: Response) {
  if (res.status === 401) {
    if (typeof window !== "undefined") window.location.href = "/login";
    return null;
  }
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

const STAFF_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function apiGet(path: string) {
  const res = await fetch(`${STAFF_BASE_URL}${path}`, { headers: getStaffHeaders() });
  return handleStaffResponse(res);
}

export async function apiPost(path: string, body: unknown) {
  const res = await fetch(`${STAFF_BASE_URL}${path}`, {
    method: "POST",
    headers: getStaffHeaders(),
    body: JSON.stringify(body),
  });
  return handleStaffResponse(res);
}

export async function apiPatch(path: string, body: unknown) {
  const res = await fetch(`${STAFF_BASE_URL}${path}`, {
    method: "PATCH",
    headers: getStaffHeaders(),
    body: JSON.stringify(body),
  });
  return handleStaffResponse(res);
}
