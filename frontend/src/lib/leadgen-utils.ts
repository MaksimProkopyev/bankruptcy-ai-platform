export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatRelative(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "только что";
  if (diffMins < 60) return `${diffMins} мин назад`;
  if (diffHours < 24) return `${diffHours} ч назад`;
  if (diffDays === 1) return "вчера";
  return `${diffDays} дн назад`;
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export const FUNNEL_STAGE_LABELS: Record<string, string> = {
  incoming: "Входящие",
  contacted: "Контакт",
  qualifying: "Квалификация",
  hot: "Горячие",
  ready_to_convert: "Готов к конвертации",
};

export const STATUS_LABELS: Record<string, string> = {
  new: "Новый",
  in_progress: "В работе",
  qualified: "Квалифицирован",
  disqualified: "Дисквалифицирован",
  converted: "Конвертирован",
  spam: "Спам",
};

export const API_BASE = "http://localhost:8002";
