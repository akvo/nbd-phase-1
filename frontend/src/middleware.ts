import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const SESSION_COOKIE_NAME = "nbd_session";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const sessionCookie = request.cookies.get(SESSION_COOKIE_NAME);

  // Protect /admin/* routes - redirect to /login if no session cookie
  if (pathname.startsWith("/admin")) {
    if (!sessionCookie?.value) {
      const loginUrl = new URL("/login", request.url);
      // Preserve the intended destination for redirect after login
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // Redirect /login to /admin/data if already authenticated
  if (pathname === "/login") {
    if (sessionCookie?.value) {
      return NextResponse.redirect(new URL("/admin/data", request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*", "/login"],
};
