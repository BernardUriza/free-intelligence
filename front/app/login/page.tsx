import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { COOKIE, mint, sameSecret } from "../../lib/session.ts";

export const dynamic = "force-dynamic";

/**
 * The door, as a page. A `<form>` and a Server Action — no client JavaScript, like
 * everything else here.
 *
 * The `next` parameter is validated before it is followed: an open redirect turns
 * a login page into a phishing tool, because the URL people are told to trust is
 * the one that sends them somewhere else. Only same-site paths are honoured.
 */

const HOME = "/console";

function safeNext(next: string | undefined): string {
  if (!next) return HOME;
  // Must be a path on THIS site: one leading slash, and not `//evil.com` (which a
  // browser reads as a protocol-relative URL to another host) and not `/\evil.com`.
  if (!next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) return HOME;
  return next;
}

async function signIn(formData: FormData) {
  "use server";

  const expected = process.env.AIRE_CONSOLE_PASSWORD;
  if (!expected) throw new Error("AIRE_CONSOLE_PASSWORD is not set.");

  const typed = String(formData.get("password") ?? "");
  const next = safeNext(String(formData.get("next") ?? ""));

  if (!sameSecret(typed, expected)) {
    redirect(`/login?wrong=1${next === HOME ? "" : `&next=${encodeURIComponent(next)}`}`);
  }

  (await cookies()).set(COOKIE, await mint(expected), {
    httpOnly: true, // JavaScript can never read it, so a stray XSS cannot steal it
    secure: process.env.NODE_ENV === "production", // TLS only, once deployed
    sameSite: "lax", // no cross-site request rides in with the session
    path: "/",
    maxAge: 7 * 24 * 60 * 60,
  });

  redirect(next);
}

export default async function Login({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; wrong?: string }>;
}) {
  const { next, wrong } = await searchParams;

  return (
    <div className="gate">
      <form action={signIn}>
        <h1>AIRE front 🌬️</h1>
        <p className="sub">
          The waiter — a read-only console over the database <code>aire-server</code> writes.
        </p>

        <input type="hidden" name="next" value={safeNext(next)} />
        <input
          type="password"
          name="password"
          placeholder="password"
          autoFocus
          required
          autoComplete="current-password"
        />
        <button>Enter</button>

        {wrong && <p className="wrong">Wrong password.</p>}
      </form>
    </div>
  );
}
