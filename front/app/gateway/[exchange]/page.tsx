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
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  return (content as Block[])
    .filter((b) => b?.type === "text" && b.text)
    .map((b) => b.text)
    .join("\n");
}

function toolsOf(content: unknown): string[] {
  if (!Array.isArray(content)) return [];
  return (content as Block[])
    .filter((b) => b?.type === "tool_use" || b?.type === "server_tool_use")
    .map((b) => b.name ?? "tool")
    .filter(Boolean);
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
        {messages.slice(-6).map((m, i) => {
          const text = textOf(m.content);
          if (!text) return null;
          return (
            <div key={i} style={{ opacity: m.role === "user" ? 0.85 : 1 }}>
              <span style={{ color: m.role === "user" ? "#7aa2f7" : "#9ece6a" }}>
                {m.role === "user" ? "›" : "⏺"}
              </span>{" "}
              <span style={{ whiteSpace: "pre-wrap" }}>{text}</span>
            </div>
          );
        })}
        {tools.length > 0 && (
          <div style={{ opacity: 0.75 }}>
            {tools.map((t, i) => (
              <code key={i} style={{ marginRight: "0.5rem" }}>⚒ {t}</code>
            ))}
          </div>
        )}
        {answer && (
          <div>
            <span style={{ color: "#9ece6a" }}>⏺</span>{" "}
            <span style={{ whiteSpace: "pre-wrap" }}>{answer}</span>
          </div>
        )}
        {!answer && tools.length === 0 && (
          <p className="empty">the response half is not in the log (yet).</p>
        )}
      </div>
    </Shell>
  );
}
