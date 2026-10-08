import { NextResponse, type NextRequest } from "next/server";

/**
 * The landing's one moving part, and the second route that skips the door.
 *
 * It discloses nothing about the database — no schema, no row, not even that a
 * database exists — which is the whole test an unauthenticated route here has to
 * pass. It reads no Postgres at all: it forwards a sentence to the droplet's
 * model and returns two words.
 *
 * The Bearer token stays server-side. A browser calling the droplet directly
 * would have to hold a credential that can also spend Anthropic tokens, so it
 * never gets one: the visitor talks to this route, this route talks to the gate.
 */

export const dynamic = "force-dynamic";

const MAX_CHARS = 400;

export async function POST(request: NextRequest) {
  const gate = process.env.AIRE_GATE_URL;
  const token = process.env.AIRE_AUTH_TOKEN;
  if (!gate || !token) {
    return NextResponse.json({ detail: "the generator is not wired up" }, { status: 503 });
  }

  let text = "";
  try {
    text = String(((await request.json()) as { text?: unknown }).text ?? "").trim();
  } catch {
    return NextResponse.json({ detail: "expected JSON" }, { status: 400 });
  }
  if (!text) return NextResponse.json({ detail: "say something first" }, { status: 400 });

  try {
    const upstream = await fetch(`${gate.replace(/\/$/, "")}/nickname`, {
      method: "POST",
      headers: { "content-type": "application/json", authorization: `Bearer ${token}` },
      body: JSON.stringify({ text: text.slice(0, MAX_CHARS) }),
      signal: AbortSignal.timeout(20_000),
    });
    const body = await upstream.json();
    return NextResponse.json(body, { status: upstream.status });
  } catch {
    // Never leak the gate's URL or the reason — a stranger is on the other end.
    return NextResponse.json({ detail: "the generator is asleep" }, { status: 502 });
  }
}
