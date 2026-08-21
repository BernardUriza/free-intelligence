/**
 * Rendering helpers for the claude memory pages — pure presentation over the
 * entries `db.ts` reads. No Postgres in here (the waiter's hands stay in db.ts).
 */
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";

const CASITA_PREFIX = "-opt-aire-workspaces-";
const SCRATCH_RE = /^\d{8}T\d{6}Z-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-/;

/** Human name for a project_key: strip the workspaces prefix and, for scratch
 *  casitas, the timestamp+uuid — "…-libro-hormigas" → "libro-hormigas". */
export function folderName(projectKey: string): string {
  let name = projectKey.startsWith(CASITA_PREFIX) ? projectKey.slice(CASITA_PREFIX.length) : projectKey;
  name = name.replace(SCRATCH_RE, "");
  return name || projectKey;
}

/** The casita's fixed prompt, folded away — shown on the folder page and on
 *  every session page, so the reader sees what the agent stands on. Null
 *  renders nothing: a casita without a CLAUDE.md has nothing to show. */
export function CasitaPrompt({ text }: { text: string | null }) {
  if (!text) return null;
  return (
    <details className="panel">
      <summary>
        CLAUDE.md · the casita&apos;s fixed prompt · {text.length.toLocaleString("en-US")} chars
      </summary>
      <Md text={text} />
    </details>
  );
}

/** The casita's DIRECTORY name on the daemon's disk — the artifacts door's
 *  project id. Unlike folderName, the scratch timestamp+uuid must stay: it is
 *  part of the real path. Null for keys outside the workspaces tree (a Mac
 *  cwd mirrored by the SSH door has no artifacts door behind it). */
export function casitaDir(projectKey: string): string | null {
  return projectKey.startsWith(CASITA_PREFIX) ? projectKey.slice(CASITA_PREFIX.length) : null;
}

/** A transcript's weight in bytes → a human size. The daemon stores no cost
 *  (backlog #8: total_cost_usd never lands in the store), so weight is the
 *  honest "how much each casita holds" — the JSON bytes of its transcript. */
export function humanBytes(bytes: number): string {
  if (!bytes) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
  return text ? (text.length > 80 ? text.slice(0, 77) + "…" : text) : "(no prompt)";
}

/** "40s ago / 12min ago / Jul 14" from a bigint-ms string. */
export function freshness(mtimeMs: string): string {
  const ms = Number(mtimeMs);
  if (!ms) return "";
  const diff = Date.now() - ms;
  if (diff < 60_000) return `${Math.max(1, Math.round(diff / 1000))}s ago`;
  if (diff < 3_600_000) return `${Math.round(diff / 60_000)}min ago`;
  if (diff < 86_400_000) return `${Math.round(diff / 3_600_000)}h ago`;
  return new Date(ms).toLocaleDateString("en-US", { day: "numeric", month: "short" });
}

/** The speaker mark and the words — `›` for the caller, `⏺` for the model. The
 *  one way both transcript views (/claude and /gateway) draw a spoken line. */
export function Line({ who, text }: { who: "caller" | "model"; text: string }) {
  return (
    <>
      <span className={who}>{who === "caller" ? "›" : "⏺"}</span>{" "}
      <span className="words">{text}</span>
    </>
  );
}

/** A turn's text rendered as markdown, server-side — real React elements, no
 *  raw HTML pass-through, because gateway content is other people's bytes.
 *  `remark-breaks` keeps single newlines as line breaks: transcripts are not
 *  prose, and collapsing their lines rewrites what was said. */
export function Md({ text }: { text: string }) {
  return (
    <div className="md">
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{text}</ReactMarkdown>
    </div>
  );
}
