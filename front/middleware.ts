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
 * Three routes skip it, and each passes the same test: it discloses nothing about
 * the schema, the data, or the existence of either.
 *
 * - `/api/health` — a liveness probe cannot carry a credential. It reports that it
 *   can read; it never reports WHAT.
 * - `/` — the landing (backlog #32), a page that opens no database connection.
 *   Everything the console actually shows moved to `/console`, and a visitor who is
 *   already signed in never sees the landing: they are sent straight there.
 * - `/api/nickname` — the landing's generator. It forwards a sentence to the
 *   droplet's model and returns two words; it touches no Postgres either.
 * - `/api/access` — the request-access button. It asks the daemon to mail Bernard
 *   a signed link; it reads nothing back.
 * - `/approved` — where that link lands. An email must open on whatever device is
 *   in hand, so it cannot sit behind the console password. It states nothing it
 *   was not handed in the URL.
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

  if (pathname === "/") {
    // The landing is for strangers. Someone already inside gets the room, not the
    // poster on its door.
    if (signedIn) return NextResponse.redirect(new URL("/console", request.url));
    return NextResponse.next();
  }

  if (pathname === "/login") {
    // Already in? Don't show the door to someone standing inside the room.
    if (signedIn) return NextResponse.redirect(new URL("/console", request.url));
    return NextResponse.next();
  }

  if (signedIn) return NextResponse.next();

  // Remember where they were going, so signing in lands them there and not on a
  // generic home page they did not ask for.
  const login = new URL("/login", request.url);
  const wanted = pathname + search;
  if (wanted !== "/console") login.searchParams.set("next", wanted);
  return NextResponse.redirect(login);
}

export const config = {
  matcher: [
    "/((?!api/health|api/nickname|api/access|approved|_next/static|_next/image|favicon.ico).*)",
  ],
};
