import Link from "next/link";
import Shell from "../../../components/Shell.tsx";
import { gatewayExchange } from "../../../lib/db.ts";
import { freshness } from "../../../lib/claude.tsx";

export const dynamic = "force-dynamic";

type Block = { type?: string; text?: string; name?: string; content?: unknown };
type Msg = { role?: string; content?: unknown };

/** Pull the readable text out of an Anthropic content array (or a bare string,
 *  which the Messages API also accepts for a user turn). */
function textOf(content: unknown): string {
  return blocksOf(content).join("\n");
}

/** The text blocks of a message, kept SEPARATE — a turn is not one string. A
 *  Claude Code request carries pages of scaffolding in its own blocks, and
 *  joining them first is what buries the human sentence. */
function blocksOf(content: unknown): string[] {
  if (typeof content === "string") return [content];
  if (!Array.isArray(content)) return [];
  return (content as Block[])
    .filter((b) => b?.type === "text" && b.text)
    .map((b) => b.text as string);
}

const SCAFFOLD = /^<(system-reminder|session|recent_conversation|turn_context)\b/;

/** Split a block into the machine's scaffolding and the part a human wrote.
 *  The scaffolding opens the block and the real sentence trails it, so the cut
 *  is after the LAST closing tag. A block with nothing after it is all
 *  scaffolding; a block that never opened with one is all readable. */
function split(text: string): { scaffold: string; readable: string } {
  if (!SCAFFOLD.test(text.trimStart())) return { scaffold: "", readable: text };
  const close = text.lastIndexOf("</");
  const end = close === -1 ? -1 : text.indexOf(">", close);
  if (end === -1) return { scaffold: text, readable: "" };
  return { scaffold: text.slice(0, end + 1), readable: text.slice(end + 1).trim() };
}

function toolsOf(content: unknown): string[] {
  if (!Array.isArray(content)) return [];
  return (content as Block[])
    .filter((b) => b?.type === "tool_use" || b?.type === "server_tool_use")
    .map((b) => b.name ?? "tool")
    .filter(Boolean);
}

/** The speaker mark and the words — `›` for the caller, `⏺` for the model. */
function Line({ role, text }: { role?: string; text: string }) {
  return (
    <>
      <span style={{ color: role === "user" ? "#7aa2f7" : "#9ece6a" }}>
        {role === "user" ? "›" : "⏺"}
      </span>{" "}
      <span style={{ whiteSpace: "pre-wrap" }}>{text}</span>
    </>
  );
}

/** One block of one message: the scaffolding folded away, the sentence shown. */
function TurnBlock({ role, block }: { role?: string; block: string }) {
  const { scaffold, readable } = split(block);
  if (!scaffold && !readable) return null;
  return (
    <div style={{ opacity: role === "user" ? 0.85 : 1 }}>
      {scaffold && (
        <details style={{ marginBottom: readable ? "0.5rem" : 0, opacity: 0.6 }}>
          <summary style={{ cursor: "pointer" }}>
            contexto del sistema · {scaffold.length.toLocaleString("en-US")} chars
          </summary>
          <span style={{ whiteSpace: "pre-wrap" }}>{scaffold}</span>
        </details>
      )}
      {readable && <Line role={role} text={readable} />}
    </div>
  );
}

function Tools({ names }: { names: string[] }) {
  if (names.length === 0) return null;
  return (
    <div style={{ opacity: 0.75 }}>
      {names.map((t, i) => (
        <code key={i} style={{ marginRight: "0.5rem" }}>⚒ {t}</code>
      ))}
    </div>
  );
}

/** One relayed turn, both halves. The daemon stored the raw API bodies; this is
 *  the waiter reading them back as a conversation instead of a jsonb blob. */
export default async function ExchangePage({
  params,
}: {
  params: Promise<{ exchange: string }>;
}) {
  const { exchange } = await params;
  const turn = await gatewayExchange(exchange);

  if (!turn) {
    return (
      <Shell active="~gateway">
        <h1>gateway</h1>
        <p className="empty">no exchange <code>{exchange}</code> in the log.</p>
      </Shell>
    );
  }

  const req = (turn.request ?? {}) as { messages?: Msg[]; system?: unknown };
  const res = (turn.response ?? {}) as { content?: unknown; stop_reason?: string };
  const messages = Array.isArray(req.messages) ? req.messages : [];
  const answer = textOf(res.content);
  const tools = toolsOf(res.content);

  return (
    <Shell active="~gateway">
      <h1>one turn through the door</h1>
      <p className="sub">
        <Link href="/gateway">← gateway</Link> · <code>{exchange}</code> ·{" "}
        {turn.model ?? "—"} · {freshness(turn.ts)}
      </p>
      <div className="panel" style={{ display: "grid", gap: "0.9rem", padding: "1rem" }}>
        {messages.slice(-6).flatMap((m, i) =>
          blocksOf(m.content).map((block, j) => (
            <TurnBlock key={`${i}-${j}`} role={m.role} block={block} />
          )),
        )}
        <Tools names={tools} />
        {answer && (
          <div>
            <Line role="assistant" text={answer} />
          </div>
        )}
        {!answer && tools.length === 0 && (
          <p className="empty">the response half is not in the log (yet).</p>
        )}
      </div>
    </Shell>
  );
}
