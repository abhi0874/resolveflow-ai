import { NextResponse, type NextRequest } from "next/server";
import { appMode } from "@/lib/app-mode";
import { accountDestination, accountEntry, accountPathHeader } from "@/lib/account-navigation";
import { isSessionToken, sessionCookieNames } from "@/lib/account-cookie";

export function proxy(request: NextRequest) {
  if (appMode() === "demo") return accountRedirect(request, "/demo");
  const url = request.nextUrl.clone();
  url.searchParams.delete("_rsc");
  const destination = accountDestination(url.pathname + url.search);
  const hasSessionCookie = sessionCookieNames.some((name) =>
    isSessionToken(request.cookies.get(name)?.value),
  );
  if (!hasSessionCookie) return accountRedirect(request, accountEntry("/login", destination));
  const headers = new Headers(request.headers);
  headers.set(accountPathHeader, destination);
  const response = NextResponse.next({ request: { headers } });
  response.headers.set("Cache-Control", "private, no-store");
  return response;
}

function accountRedirect(request: NextRequest, location: string) {
  const response = NextResponse.redirect(new URL(location, request.url));
  response.headers.set("Cache-Control", "private, no-store");
  return response;
}

export const config = { matcher: "/app/:path*" };
