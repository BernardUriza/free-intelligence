/**
 * The casita's fixed prompt (CLAUDE.md), read through the daemon's artifacts
 * door (#22b). It is a file on the droplet's DISK, not a database row, so it
 * cannot come through lib/db.ts — the daemon remains the only thing touching
 * disk, and the front asks it over HTTP with its own canary credential, the
 * same way any consumer would. AIRE_AUTH_TOKEN here is the front's own canary
 * credential (secret `aire-canary-token` on the container — the same pair the
 * nickname and access routes already use). Null means the casita has none, the
 * credential is unset, or the door is unreachable: the view then shows nothing
 * rather than an invented empty file.
 */

const GATE = process.env.AIRE_GATE_URL ?? "https://gate.bernarduriza.com";

export async function casitaClaudeMd(dir: string | null): Promise<string | null> {
  const token = process.env.AIRE_AUTH_TOKEN;
  if (!token || !dir) return null;
  try {
    const res = await fetch(
      `${GATE}/projects/${encodeURIComponent(dir)}/artifacts/CLAUDE.md`,
      {
        headers: { authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(5000),
        cache: "no-store",
      },
    );
    if (!res.ok) return null;
    return await res.text();
  } catch {
    return null;
  }
}
