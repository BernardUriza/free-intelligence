/**
 * The AIRE-door client for canary consumers (backlog #9's proof-in-action).
 *
 * This is the OTHER half of the front: the console READS the database (the
 * waiter, `lib/db.ts`); a consumer here CALLS the daemon's HTTP door and lets it
 * write. It never touches Postgres, so `read-only-waiter` is untouched — a
 * consumer is an HTTP client of AIRE, not a second pen.
 *
 * SERVER-SIDE ONLY. `AIRE_AUTH_TOKEN` is the LLM door's spend key; it lives in
 * the front's server env and must never reach the browser (these helpers run in
 * Server Components / actions only). The gate speaks SSE even for `complete`, so
 * we read the stream and pull the `result` event's text out.
 */

const GATE = process.env.AIRE_GATE_URL ?? "";
const TOKEN = process.env.AIRE_AUTH_TOKEN ?? "";

export type Turn = { text: string; costUsd: number | null; session: string };

function parseSse(body: string): Turn | null {
  let out: Turn | null = null;
  for (const line of body.split("\n")) {
    if (!line.startsWith("data: ")) continue;
    const ev = JSON.parse(line.slice(6));
    if (ev.type === "result") {
      out = { text: ev.result.text, costUsd: ev.result.usage?.total_cost_usd ?? null,
              session: ev.result.session_id ?? "" };
    }
  }
  return out;
}

/** Set a casita's FIXED prompt once (its CLAUDE.md), so later turns send only the
 *  changing values. Idempotent — safe to call before every turn. */
export async function init(project: string, claudeMd: string): Promise<void> {
  if (!GATE || !TOKEN) throw new Error("AIRE_GATE_URL / AIRE_AUTH_TOKEN not set — no door to call.");
  const res = await fetch(`${GATE}/projects/${project}/init`, {
    method: "POST",
    headers: { Authorization: `Bearer ${TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify({ claude_md: claudeMd }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`AIRE init ${res.status}: ${await res.text()}`);
}

/** One `complete` turn through the AIRE door. Throws if the door is unset/down. */
export async function ask(project: string, session: string, message: string): Promise<Turn> {
  if (!GATE || !TOKEN) throw new Error("AIRE_GATE_URL / AIRE_AUTH_TOKEN not set — no door to call.");
  const res = await fetch(`${GATE}/projects/${project}/sessions/${session}/messages`, {
    method: "POST",
    headers: { Authorization: `Bearer ${TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify({ mode: "complete", message }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`AIRE door ${res.status}: ${await res.text()}`);
  const turn = parseSse(await res.text());
  if (!turn) throw new Error("AIRE door returned no result event.");
  return turn;
}
