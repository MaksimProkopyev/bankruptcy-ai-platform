/**
 * Case status configuration — labels, colors, groups.
 */

export const CASE_STATUSES: Record<string, { label: string; color: string; group: string }> = {
  lead:                    { label: "Лид",                color: "bg-surface-muted text-text-muted",     group: "funnel" },
  qualification:           { label: "Квалификация",       color: "bg-info/10 text-info",     group: "funnel" },
  consultation:            { label: "Консультация",       color: "bg-info/10 text-info",     group: "funnel" },
  contract_signing:        { label: "Подписание",         color: "bg-primary/10 text-primary", group: "funnel" },
  document_collection:     { label: "Сбор документов",    color: "bg-warning/10 text-warning", group: "preparation" },
  document_review:         { label: "Проверка документов", color: "bg-warning/10 text-warning", group: "preparation" },
  application_preparation: { label: "Подготовка заявления", color: "bg-warning/10 text-warning", group: "preparation" },
  application_filed:       { label: "Подано в суд",       color: "bg-primary/10 text-primary", group: "court" },
  court_accepted:          { label: "Принято судом",      color: "bg-primary/10 text-primary", group: "court" },
  hearing_scheduled:       { label: "Заседание назначено", color: "bg-primary/10 text-primary", group: "court" },
  procedure_started:       { label: "Процедура введена",  color: "bg-primary/10 text-primary", group: "court" },
  creditors_registry:      { label: "Реестр кредиторов",  color: "bg-primary/10 text-primary", group: "court" },
  creditors_meeting:       { label: "Собрание кредиторов", color: "bg-primary/10 text-primary", group: "court" },
  asset_realization:       { label: "Реализация",         color: "bg-danger/10 text-danger",     group: "court" },
  restructuring:           { label: "Реструктуризация",   color: "bg-warning/10 text-warning",   group: "court" },
  fu_report:               { label: "Отчёт ФУ",          color: "bg-info/10 text-info",     group: "completion" },
  completion:              { label: "Завершение",         color: "bg-success/10 text-success",   group: "completion" },
  debt_discharged:         { label: "Долги списаны",      color: "bg-success/10 text-success",   group: "completed" },
  on_hold:                 { label: "Приостановлено",     color: "bg-surface-muted text-text-muted",     group: "special" },
  rejected:                { label: "Отказ",              color: "bg-danger/10 text-danger",       group: "special" },
  cancelled:               { label: "Отменено",           color: "bg-danger/10 text-danger",       group: "special" },
  settlement:              { label: "Мировое соглашение", color: "bg-info/10 text-info",     group: "special" },
};

export function getStatusLabel(status: string): string {
  return CASE_STATUSES[status]?.label || status;
}

export function getStatusColor(status: string): string {
  return CASE_STATUSES[status]?.color || "bg-gray-100 text-gray-700";
}

export function formatCurrency(amount: number | undefined | null): string {
  if (!amount) return "—";
  return new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 }).format(amount);
}

export function formatDate(dateStr: string | undefined | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("ru-RU", { day: "numeric", month: "short", year: "numeric" });
}

export const RISK_COLORS: Record<string, string> = {
  low: "bg-success/10 text-success",
  medium: "bg-warning/10 text-warning",
  high: "bg-danger/10 text-danger",
};
