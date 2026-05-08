import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Middleware handles three zones:
 *
 * 1. Public site (/, /uslugi, /blog, etc.) — no auth needed
 * 2. Client cabinet (/lk/*) — requires client_token cookie/header
 * 3. CRM panel (/crm/*) — requires staff token cookie/header
 *
 * Auth tokens are validated client-side (JWT decode).
 * This middleware only checks for token presence and redirects.
 */

export function middleware(request: NextRequest) {
  const host = request.headers.get('host') || ''
  const { pathname } = request.nextUrl

  // Hostname-based routing
  if (host.startsWith('crm.') && !pathname.startsWith('/crm')) {
    return NextResponse.redirect(new URL('/crm/dashboard', request.url))
  }

  if (host.startsWith('lk.') && !pathname.startsWith('/lk')) {
    return NextResponse.redirect(new URL('/lk', request.url))
  }

  // Client cabinet — redirect to login if no token
  if (pathname.startsWith("/lk") && !pathname.startsWith("/lk/login")) {
    const clientToken =
      request.cookies.get("client_token")?.value ||
      request.headers.get("x-client-token");

    if (!clientToken) {
      const loginUrl = new URL("/lk/login", request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // CRM panel — redirect to CRM login if no staff token
  if (pathname.startsWith("/crm") && !pathname.startsWith("/crm/login")) {
    const staffToken =
      request.cookies.get("staff_token")?.value ||
      request.headers.get("authorization");

    if (!staffToken) {
      return NextResponse.redirect(new URL("/crm/login", request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
