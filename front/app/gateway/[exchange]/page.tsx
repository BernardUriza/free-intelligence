import Link from "next/link";
import Shell from "../../../components/Shell.tsx";
import { gatewayExchange } from "../../../lib/db.ts";
import { freshness } from "../../../lib/claude.tsx";
import { blocksOf, MessageCard, ResponseCard, type Msg } from "../../../lib/gateway.tsx";

export const dynamic = "force-dynamic";

/** How many trailing request messages to show — the tail is where the human
 *  turn lives; the head is history the caller resent. */
const SHOWN_MESSAGES = 6;

/** One relayed turn, both halves, raw. The daemon stored the API bodies; this
 *  is the waiter reading them back as a conversation instead of a jsonb blob. */
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

  return (
    <Shell active="~gateway">
      <h1>one turn through the door</h1>
      <p className="sub">
        <Link href="/gateway">← gateway</Link>
        {turn.session_id && (
          <>
            {" "}· <Link href={`/gateway/s/${turn.session_id}`}>conversation</Link>
          </>
        )}{" "}
        · <code>{exchange}</code> · {turn.model ?? "—"} · {freshness(turn.ts)}
      </p>

      <h2 className="sect">
        request · {shown.length} of {messages.length} messages
      </h2>
      {shown.map((m, i) => (
        <MessageCard key={i} role={m.role} blocks={blocksOf(m.content)} />
      ))}

      <h2 className="sect">response</h2>
      <ResponseCard
        model={turn.model}
        content={res.content}
        stopReason={res.stop_reason}
        inputTokens={res.usage?.input_tokens}
        outputTokens={res.usage?.output_tokens}
      />
    </Shell>
  );
}
