import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const host = request.headers.get('host') || ''
  const { pathname } = request.nextUrl

  // staff.nssb-maximum.ru → /dashboard (staff zone)
  if (host.startsWith('staff.')) {
    if (pathname === '/') {
      return NextResponse.redirect(new URL('/dashboard', request.url))
    }
    // Auth check for staff pages
    if (
      (pathname.startsWith('/dashboard') ||
       pathname.startsWith('/tasks') ||
       pathname.startsWith('/ideas')) &&
      !pathname.startsWith('/login')
    ) {
      const staffToken =
        request.cookies.get("staff_token")?.value ||
        request.headers.get("authorization");
      if (!staffToken) {
        return NextResponse.redirect(new URL('/login', request.url))
      }
    }
    return NextResponse.next()
  }

  // crm.nssb-maximum.ru → /crm
  if (host.startsWith('crm.') && !pathname.startsWith('/crm')) {
    return NextResponse.redirect(new URL('/crm/dashboard', request.url))
  }

  // lk.nssb-maximum.ru → /lk
  if (host.startsWith('lk.') && !pathname.startsWith('/lk')) {
    return NextResponse.redirect(new URL('/lk', request.url))
  }

  // Client cabinet auth
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

  // CRM auth
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
