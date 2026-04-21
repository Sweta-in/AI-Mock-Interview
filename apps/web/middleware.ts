import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PROTECTED_PATHS = ['/dashboard', '/interview'];
const AUTH_PATHS = ['/auth/login', '/auth/signup'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check for Supabase session cookie
  const supabaseCookies = request.cookies.getAll();
  const hasSession = supabaseCookies.some(
    (cookie) => cookie.name.includes('auth-token') || cookie.name.includes('sb-')
  );

  // Protect authenticated routes
  const isProtected = PROTECTED_PATHS.some((path) => pathname.startsWith(path));
  if (isProtected && !hasSession) {
    const loginUrl = new URL('/auth/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Redirect authenticated users away from auth pages
  const isAuthPage = AUTH_PATHS.some((path) => pathname === path);
  if (isAuthPage && hasSession) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/interview/:path*', '/auth/:path*'],
};
