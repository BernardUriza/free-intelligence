/**
 * Rendering helpers for the claude memory pages — pure presentation over the
 * entries `db.ts` reads. No Postgres in here (the waiter's hands stay in db.ts).
 */

const CASITA_PREFIX = "-opt-aire-workspaces-";
const SCRATCH_RE = /^\d{8}T\d{6}Z-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-/;

/** Human name for a project_key: strip the workspaces prefix and, for scratch
 *  casitas, the timestamp+uuid — "…-libro-hormigas" → "libro-hormigas". */
export function folderName(projectKey: string): string {
  let name = projectKey.startsWith(CASITA_PREFIX) ? projectKey.slice(CASITA_PREFIX.length) : projectKey;
  name = name.replace(SCRATCH_RE, "");
  return name || projectKey;
}

type Block = { type?: string; text?: string; name?: string; input?: unknown };
type Message = { content?: string | Block[] };
type Entry = { type?: string; message?: Message; uuid?: string };

/** The text of an entry's message — string content or joined text blocks. */
export function entryText(entry: unknown): string {
  const e = entry as Entry;
  const content = e?.message?.content;
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content.filter((b) => b?.type === "text").map((b) => b.text ?? "").join("");
  }
  return "";
}

/** Tool calls inside an assistant entry, for the chips. */
export function entryTools(entry: unknown): { name: string; summary: string }[] {
  const content = (entry as Entry)?.message?.content;
  if (!Array.isArray(content)) return [];
  return content
    .filter((b) => b?.type === "tool_use")
    .map((b) => {
      const input = b.input && typeof b.input === "object" ? Object.values(b.input as Record<string, unknown>) : [];
      const first = input.length ? String(input[0]) : "";
      return { name: b.name ?? "?", summary: first.length > 60 ? first.slice(0, 57) + "…" : first };
    });
}

/** Session title: the first user prompt, trimmed to one line. */
export function sessionTitle(firstUser: unknown): string {
  const text = entryText(firstUser).trim().split("\n")[0];
  return text ? (text.length > 80 ? text.slice(0, 77) + "…" : text) : "(sin prompt)";
}

/** "hace 40s / hace 12min / 14 jul" from a bigint-ms string. */
export function freshness(mtimeMs: string): string {
  const ms = Number(mtimeMs);
  if (!ms) return "";
  const diff = Date.now() - ms;
  if (diff < 60_000) return `hace ${Math.max(1, Math.round(diff / 1000))}s`;
  if (diff < 3_600_000) return `hace ${Math.round(diff / 60_000)}min`;
  if (diff < 86_400_000) return `hace ${Math.round(diff / 3_600_000)}h`;
  return new Date(ms).toLocaleDateString("es-MX", { day: "numeric", month: "short" });
}
