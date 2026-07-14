import { NextResponse, type NextRequest } from "next/server";
import { COOKIE, valid } from "./lib/session.ts";

/**
 * The door. Everything behind it is a read of the owner's database, so there is no
 * such thing as a page here that a stranger may see.
 *
 * It guards the APP, not the deployment — it holds identically under `docker run`,
 * `next start` and Container Apps. A console that is private only because the
 * infrastructure happens to be configured right is one `az` flag away from public.
 *
 * It was HTTP Basic for exactly one deploy. The browser's native prompt cannot be
 * styled, cannot be logged out of, and is a hostile little box on a phone — and it
 * broke automated navigation outright (`ERR_INVALID_AUTH_CREDENTIALS`). A login is
 * a page, like every other page here: server-rendered HTML, no client JavaScript.
 *
 * `/api/health` is the single exception, because a liveness probe cannot carry a
 * credential — so it is also the one route that must give nothing away. It reports
 * that it can read; it never reports WHAT.
 */

export async function middleware(request: NextRequest) {
  const expected = process.env.AIRE_CONSOLE_PASSWORD;

  // No password configured = the console is wide open. Fail CLOSED, loudly. The
  // alternative — serving everything because a variable is unset — is how a
  // database ends up on the public internet by omission.
  if (!expected) {
    return new NextResponse(
      "AIRE_CONSOLE_PASSWORD is not set. The console refuses to serve without a door.",
      { status: 503, headers: { "content-type": "text/plain; charset=utf-8" } },
    );
  }

  const { pathname, search } = request.nextUrl;
  const signedIn = await valid(request.cookies.get(COOKIE)?.value, expected);

  if (pathname === "/login") {
    // Already in? Don't show the door to someone standing inside the room.
    if (signedIn) return NextResponse.redirect(new URL("/", request.url));
    return NextResponse.next();
  }

  if (signedIn) return NextResponse.next();

  // Remember where they were going, so signing in lands them there and not on a
  // generic home page they did not ask for.
  const login = new URL("/login", request.url);
  const wanted = pathname + search;
  if (wanted !== "/") login.searchParams.set("next", wanted);
  return NextResponse.redirect(login);
}

export const config = {
  matcher: ["/((?!api/health|_next/static|_next/image|favicon.ico).*)"],
};
