// lk-frontend middleware. Source: DEC-016.
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Public paths — no auth required
  if (pathname === '/login' || pathname === '/') {
    return NextResponse.next()
  }

  // All other paths require client_token cookie
  const clientToken =
    request.cookies.get('client_token')?.value ||
    request.headers.get('x-client-token')

  if (!clientToken) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
