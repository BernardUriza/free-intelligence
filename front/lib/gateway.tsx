/**
 * Rendering helpers for the gateway views — the raw Anthropic API halves the
 * door relayed, drawn as role cards. Pure presentation; Postgres stays in db.ts.
 */
import Link from "next/link";
import { Md } from "./claude.tsx";

type Block = { type?: string; text?: string; name?: string };
export type Msg = { role?: string; content?: unknown };

/** The text blocks of a message, kept SEPARATE — a turn is not one string. A
 *  Claude Code request carries pages of scaffolding in its own blocks, and
 *  joining them first is what buries the human sentence. */
export function blocksOf(content: unknown): string[] {
  if (typeof content === "string") return [content];
  if (!Array.isArray(content)) return [];
  return (content as Block[])
    .filter((b) => b?.type === "text" && b.text)
    .map((b) => b.text as string);
}

/** Pull the readable text out of an Anthropic content array (or a bare string,
 *  which the Messages API also accepts for a user turn). */
export function textOf(content: unknown): string {
  return blocksOf(content).join("\n");
}

export function toolsOf(content: unknown): string[] {
  if (!Array.isArray(content)) return [];
  return (content as Block[])
    .filter((b) => b?.type === "tool_use" || b?.type === "server_tool_use")
    .map((b) => b.name ?? "tool")
    .filter(Boolean);
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

/** One message of a request, boxed: the role rail, the scaffolding folded
 *  away per block, the sentences rendered as markdown. */
export function MessageCard({ role, blocks }: { role?: string; blocks: string[] }) {
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

/** The response half as a card: the model's name on the rail, the answer as
 *  markdown, tool calls as chips, stop reason and token usage as pills. An
 *  empty half renders as the honest "not in the log (yet)". */
export function ResponseCard({
  model,
  content,
  stopReason,
  inputTokens,
  outputTokens,
  href,
}: {
  model: string | null;
  content: unknown;
  stopReason?: string | null;
  inputTokens?: number | null;
  outputTokens?: number | null;
  href?: string;
}) {
  const answer = textOf(content);
  const tools = toolsOf(content);
  if (!answer && tools.length === 0) {
    return (
      <article className="turn">
        <p className="empty">the response half is not in the log (yet).</p>
      </article>
    );
  }
  return (
    <article className="turn by-model">
      <header className="who">
        <span className="mark">⏺</span> {model ?? "model"}
      </header>
      {answer && <Md text={answer} />}
      <Tools names={tools} />
      {(stopReason || inputTokens != null || outputTokens != null || href) && (
        <footer>
          {stopReason && <span className="pill">{stopReason}</span>}
          {inputTokens != null && (
            <span className="pill">in {inputTokens.toLocaleString("en-US")}</span>
          )}
          {outputTokens != null && (
            <span className="pill">out {outputTokens.toLocaleString("en-US")}</span>
          )}
          {href && (
            <Link className="pill" href={href}>
              full turn →
            </Link>
          )}
        </footer>
      )}
    </article>
  );
}
