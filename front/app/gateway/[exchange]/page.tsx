import Link from "next/link";
import Shell from "../../../components/Shell.tsx";
import { gatewayExchange } from "../../../lib/db.ts";
import { freshness, Md } from "../../../lib/claude.tsx";

export const dynamic = "force-dynamic";

/** How many trailing request messages to show — the tail is where the human
 *  turn lives; the head is history the caller resent. */
const SHOWN_MESSAGES = 6;

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

/** One message of the request, boxed: the role rail, the scaffolding folded
 *  away per block, the sentences shown. */
function MessageCard({ role, blocks }: { role?: string; blocks: string[] }) {
  const halves = blocks.map(split).filter((h) => h.scaffold || h.readable);
  if (halves.length === 0) return null;
  const caller = role === "user";
  return (
    <article className={caller ? "turn by-caller" : "turn by-model"}>
      <header className="who">
        <span className="mark">{caller ? "›" : "⏺"}</span> {caller ? "caller" : "model"}
      </header>
      {halves.map(({ scaffold, readable }, i) => (
        <div key={i}>
          {scaffold && (
            <details>
              <summary>
                system context · {scaffold.length.toLocaleString("en-US")} chars
              </summary>
              <span className="words">{scaffold}</span>
            </details>
          )}
          {readable && <Md text={readable} />}
        </div>
      ))}
    </article>
  );
}

function Tools({ names }: { names: string[] }) {
  if (names.length === 0) return null;
  return (
    <div className="chips">
      {names.map((t, i) => (
        <code key={i}>⚒ {t}</code>
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

  const req = (turn.request ?? {}) as { messages?: Msg[] };
  const res = (turn.response ?? {}) as {
    content?: unknown;
    stop_reason?: string;
    usage?: { input_tokens?: number; output_tokens?: number };
  };
  const messages = Array.isArray(req.messages) ? req.messages : [];
  const shown = messages.slice(-SHOWN_MESSAGES);
  const answer = textOf(res.content);
  const tools = toolsOf(res.content);

  return (
    <Shell active="~gateway">
      <h1>one turn through the door</h1>
      <p className="sub">
        <Link href="/gateway">← gateway</Link> · <code>{exchange}</code> ·{" "}
        {turn.model ?? "—"} · {freshness(turn.ts)}
      </p>

      <h2 className="sect">
        request · {shown.length} of {messages.length} messages
      </h2>
      {shown.map((m, i) => (
        <MessageCard key={i} role={m.role} blocks={blocksOf(m.content)} />
      ))}

      <h2 className="sect">response</h2>
      {answer || tools.length > 0 ? (
        <article className="turn by-model">
          <header className="who">
            <span className="mark">⏺</span> {turn.model ?? "model"}
          </header>
          {answer && <Md text={answer} />}
          <Tools names={tools} />
          {(res.stop_reason || res.usage) && (
            <footer>
              {res.stop_reason && <span className="pill">{res.stop_reason}</span>}
              {res.usage?.input_tokens != null && (
                <span className="pill">in {res.usage.input_tokens.toLocaleString("en-US")}</span>
              )}
              {res.usage?.output_tokens != null && (
                <span className="pill">out {res.usage.output_tokens.toLocaleString("en-US")}</span>
              )}
            </footer>
          )}
        </article>
      ) : (
        <article className="turn">
          <p className="empty">the response half is not in the log (yet).</p>
        </article>
      )}
    </Shell>
  );
}
