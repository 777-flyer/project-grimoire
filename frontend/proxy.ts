import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/** Prevents authenticated pages from being cached after logout. */
export function proxy(request: NextRequest) {
  const response = NextResponse.next();
  response.headers.set("Cache-Control", "no-store, no-cache, must-revalidate, private");
  return response;
}

export const config = {
  matcher: ["/dashboard/:path*", "/projects/:path*", "/admin/:path*"],
};
