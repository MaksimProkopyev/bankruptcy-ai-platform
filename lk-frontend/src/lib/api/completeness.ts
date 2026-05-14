/**
 * API client for document completeness checklist
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "API Error");
  }
  return res.json();
}

export type ChecklistItemStatus = "missing" | "uploaded" | "review" | "approved" | "rejected" | "waived";
export type MatchMethod = "manual" | "auto_type" | "auto_fuzzy" | "auto_ai";

export interface CompletenessItemResponse {
  id: string;
  checklist_item_id: string;
  name: string;
  category: string;
  required: boolean;
  description: string;
  legal_basis: string;
  how_to_get: string;
  status: ChecklistItemStatus;
  document_id: string | null;
  document_name: string | null;
  matched_by: MatchMethod | null;
  reviewer_id: string | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
  notes: string | null;
  accept_formats: string[];
  max_age_days: number | null;
}

export interface CategoryProgress {
  category: string;
  category_name: string;
  total: number;
  completed: number;
  required_total: number;
  required_completed: number;
  items: CompletenessItemResponse[];
}

export interface CompletenessProgressResponse {
  case_id: string;
  checklist_id: string;
  checklist_name: string;
  total_items: number;
  completed_items: number;
  required_items: number;
  required_completed: number;
  progress_percent: number;
  is_complete: boolean;
  categories: CategoryProgress[];
  missing_required: CompletenessItemResponse[];
}

export interface AutoMatchResponse {
  matched: number;
  details: AutoMatchDetail[];
}

export interface AutoMatchDetail {
  checklist_item_id: string;
  document_id: string;
  document_name: string;
  matched_by: MatchMethod;
  confidence: number;
}

export interface ItemUpdateRequest {
  status: ChecklistItemStatus;
  document_id?: string;
  rejection_reason?: string;
  notes?: string;
}

export async function getCompleteness(caseId: string): Promise<CompletenessProgressResponse> {
  return apiFetch<CompletenessProgressResponse>(
    `/api/v1/cases/${caseId}/completeness`,
    { method: "GET" }
  );
}

export async function initChecklist(
  caseId: string,
  checklistId?: string
): Promise<CompletenessProgressResponse> {
  return apiFetch<CompletenessProgressResponse>(
    `/api/v1/cases/${caseId}/completeness/init`,
    {
      method: "POST",
      body: JSON.stringify({ checklist_id: checklistId }),
    }
  );
}

export async function updateChecklistItem(
  caseId: string,
  itemId: string,
  update: ItemUpdateRequest
): Promise<CompletenessItemResponse> {
  return apiFetch<CompletenessItemResponse>(
    `/api/v1/cases/${caseId}/completeness/items/${itemId}`,
    {
      method: "PATCH",
      body: JSON.stringify(update),
    }
  );
}

export async function autoMatchDocuments(caseId: string): Promise<AutoMatchResponse> {
  return apiFetch<AutoMatchResponse>(
    `/api/v1/cases/${caseId}/completeness/auto-match`,
    { method: "POST" }
  );
}

export async function exportChecklist(caseId: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(
    `/api/v1/cases/${caseId}/completeness/export`,
    { method: "GET" }
  );
}
