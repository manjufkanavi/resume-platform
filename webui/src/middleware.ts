import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/", "/login", "/signup", "/templates", "/auth/callback"];
const PROTECTED_PATHS = ["/dashboard", "/upload", "/resume"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (PUBLIC_PATHS.includes(pathname)) {
    return NextResponse.next();
  }

  // Auth is enforced client-side (navbar + page gating). Keep middleware
  // non-blocking so the preview works without a live auth round-trip.
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|icons*).*)"],
};
