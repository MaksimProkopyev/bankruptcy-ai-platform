// leadgen-frontend middleware. Source: DEC-016.
// Разрешённые роли: admin, operations_director
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const ALLOWED_ROLES = ["admin", "operations_director"];

function decodeJWT(token: string) {
  try {
    const payload = token.split(".")[1];
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

function getStaffToken(request: NextRequest): string | undefined {
  const cookie = request.cookies.get("staff_token")?.value;
  if (cookie) return cookie;
  const auth = request.headers.get("authorization");
  if (auth?.startsWith("Bearer ")) return auth.slice(7);
  return undefined;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isLoginPage = pathname === "/login" || pathname.startsWith("/login/");
  if (isLoginPage) return NextResponse.next();

  const token = getStaffToken(request);
  const loginUrl = new URL("/login", request.url);

  if (!token) return NextResponse.redirect(loginUrl);

  const payload = decodeJWT(token);
  if (!payload) return NextResponse.redirect(loginUrl);

  const role: string = payload.role || "";

  if (!ALLOWED_ROLES.includes(role)) {
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon\\.ico|.*\\.png|.*\\.ico|.*\\.svg).*)",
  ],
};
