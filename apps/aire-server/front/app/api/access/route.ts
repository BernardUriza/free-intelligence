import { NextResponse, type NextRequest } from "next/server";

/**
 * The request-access button's server half. Third and last route that skips the
 * door, and it passes the same test as the other two: it discloses nothing about
 * the schema, the data, or the existence of either.
 *
 * It carries the Bearer token so the browser never has to, exactly like
 * `/api/nickname`. The daemon does the real work — signing the link and mailing
 * it — because the daemon is the half allowed to write.
 *
 * Per-IP throttling lives HERE and the global cap lives in the daemon, and both
 * are needed: from the daemon's side every visitor arrives wearing this
 * container's address, so it cannot tell one stranger from a thousand.
 */

export const dynamic = "force-dynamic";

const WINDOW_MS = 60 * 60 * 1000;
const PER_IP_PER_HOUR = 3;
const seen = new Map<string, number[]>();

function throttled(ip: string): boolean {
  const now = Date.now();
  const hits = (seen.get(ip) ?? []).filter((t) => now - t < WINDOW_MS);
  if (hits.length >= PER_IP_PER_HOUR) return true;
  hits.push(now);
  seen.set(ip, hits);
  return false;
}

export async function POST(request: NextRequest) {
  const gate = process.env.AIRE_GATE_URL;
  const token = process.env.AIRE_AUTH_TOKEN;
  if (!gate || !token) {
    return NextResponse.json({ detail: "invitations are not wired up" }, { status: 503 });
  }

  const ip = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
  if (throttled(ip)) {
    return NextResponse.json({ detail: "you have asked a few times already" }, { status: 429 });
  }

  let nickname = "";
  let blurb = "";
  try {
    const body = (await request.json()) as { nickname?: unknown; blurb?: unknown };
    nickname = String(body.nickname ?? "").trim();
    blurb = String(body.blurb ?? "").trim();
  } catch {
    return NextResponse.json({ detail: "expected JSON" }, { status: 400 });
  }
  if (!nickname) return NextResponse.json({ detail: "get a name first" }, { status: 400 });

  try {
    const upstream = await fetch(`${gate.replace(/\/$/, "")}/access/request`, {
      method: "POST",
      headers: { "content-type": "application/json", authorization: `Bearer ${token}` },
      body: JSON.stringify({ nickname: nickname.slice(0, 80), blurb: blurb.slice(0, 400) }),
      signal: AbortSignal.timeout(25_000),
    });
    return NextResponse.json(await upstream.json(), { status: upstream.status });
  } catch {
    return NextResponse.json({ detail: "could not reach the doorman" }, { status: 502 });
  }
}
