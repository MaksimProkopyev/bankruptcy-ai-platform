export function getCookie(name: string): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : "";
}

export function getToken(): string {
  return getCookie("staff_token");
}

export interface UserPayload {
  sub?: string;
  email?: string;
  role: string;
  first_name?: string;
  last_name?: string;
}

export function getUser(): UserPayload | null {
  const token = getToken();
  if (!token) return null;
  try {
    return JSON.parse(atob(token.split(".")[1])) as UserPayload;
  } catch {
    return null;
  }
}

export function logout(): void {
  document.cookie = "staff_token=; path=/; max-age=0; SameSite=Strict";
  window.location.href = "/login";
}
