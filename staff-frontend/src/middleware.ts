import { NextRequest, NextResponse } from "next/server";

function decodeJWT(token: string) {
  try {
    const payload = token.split(".")[1];
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public routes
  if (pathname === "/login") return NextResponse.next();

  const token = request.cookies.get("staff_token")?.value;

  // No token → redirect to login
  if (!token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const payload = decodeJWT(token);

  if (!payload) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const role: string = payload.role || "";

  // Admins and ops directors use the main CRM
  if (role === "admin" || role === "operations_director") {
    return NextResponse.redirect("https://crm.nssb-maximum.ru");
  }

  // Clients have no access to staff portal
  if (role === "client") {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
