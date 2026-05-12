import { getCookie } from "./auth";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function getHeaders(): Record<string, string> {
  const token = getCookie("staff_token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function handleResponse(res: Response) {
  if (res.status === 401) {
    if (typeof window !== "undefined") window.location.href = "/login";
    return null;
  }
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function apiGet(path: string) {
  const res = await fetch(`${BASE_URL}${path}`, { headers: getHeaders() });
  return handleResponse(res);
}

export async function apiPost(path: string, body: unknown) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(body),
  });
  return handleResponse(res);
}

export async function apiPatch(path: string, body: unknown) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "PATCH",
    headers: getHeaders(),
    body: JSON.stringify(body),
  });
  return handleResponse(res);
}
