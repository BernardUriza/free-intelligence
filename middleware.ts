import { NextResponse, type NextRequest } from "next/server";

/**
 * The door. Everything behind it is a read of the owner's database, so there is
 * no such thing as a page here that a stranger may see.
 *
 * HTTP Basic over TLS, deliberately, instead of the platform's built-in auth:
 * this guards the APP, not the deployment. It holds identically under `docker
 * run`, under `next start`, and behind Container Apps — a console that is only
 * private because the infrastructure happens to be configured right is a console
 * one `az` flag away from being public.
 *
 * `/api/health` is the single exception, because a liveness probe cannot carry a
 * credential — so it is also the one route that must give nothing away. It
 * reports that the process is up and reading; it does NOT report the schema.
 */

// ASCII only, and not as a style note: an HTTP header is a ByteString. The em-dash
// this repo uses everywhere else is codepoint 8212, and putting one in here made
// every request throw a TypeError inside the middleware — a 500 where a 401 belongs,
// which means no browser ever showed a login prompt. Typography is not free here.
const REALM = 'Basic realm="AIRE front - the waiter", charset="UTF-8"';

/** Compare in constant time. A byte-by-byte early return leaks the password one
 *  character at a time to anyone patient enough to measure the reply. */
function sameSecret(a: string, b: string): boolean {
  const left = new TextEncoder().encode(a);
  const right = new TextEncoder().encode(b);
  // Fold the length difference into the result instead of returning early on it.
  let diff = left.length ^ right.length;
  for (let i = 0; i < Math.max(left.length, right.length); i++) {
    diff |= (left[i] ?? 0) ^ (right[i] ?? 0);
  }
  return diff === 0;
}

function locked(): NextResponse {
  return new NextResponse("Authentication required.", {
    status: 401,
    headers: { "WWW-Authenticate": REALM },
  });
}

export function middleware(request: NextRequest) {
  const expected = process.env.AIRE_CONSOLE_PASSWORD;

  // No password configured = the console is wide open. Fail CLOSED, loudly. The
  // alternative — serve everything because a variable is unset — is how a database
  // ends up on the public internet by omission.
  if (!expected) {
    return new NextResponse(
      "AIRE_CONSOLE_PASSWORD is not set. The console refuses to serve without a door.",
      { status: 503 },
    );
  }

  const header = request.headers.get("authorization") ?? "";
  if (!header.startsWith("Basic ")) return locked();

  let decoded: string;
  try {
    decoded = atob(header.slice(6));
  } catch {
    return locked();
  }

  const password = decoded.slice(decoded.indexOf(":") + 1);
  if (!sameSecret(password, expected)) return locked();

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api/health|_next/static|_next/image|favicon.ico).*)"],
};
