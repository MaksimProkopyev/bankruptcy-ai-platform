// crm-frontend middleware. Source: DEC-016.
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Roles allowed on leadgen (others are CRM-only)
const LEADGEN_ROLES = ["admin", "operations_director"];

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

  const isPublic = pathname === "/login" || pathname.startsWith("/login/") || pathname === "/auth/sso";
  if (isPublic) return NextResponse.next();

  // CRM block — auth check for all protected routes
  const token = getStaffToken(request);
  const loginUrl = new URL("/login", request.url);

  if (!token) return NextResponse.redirect(loginUrl);

  const payload = decodeJWT(token);
  if (!payload) return NextResponse.redirect(loginUrl);

  const role: string = payload.role || "";

  // client has no access to CRM
  if (role === "client") {
    return NextResponse.redirect(loginUrl);
  }

  // Leadgen block — restrict /leadgen/* to specific roles
  if (pathname.startsWith("/leadgen/") || pathname === "/leadgen") {
    if (!LEADGEN_ROLES.includes(role)) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon\\.ico|sw\\.js|manifest\\.json|.*\\.png|.*\\.ico|.*\\.svg).*)",
  ],
};
