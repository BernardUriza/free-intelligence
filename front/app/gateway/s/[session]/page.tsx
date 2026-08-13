import Link from "next/link";
import Shell from "../../../../components/Shell.tsx";
import { gatewaySession } from "../../../../lib/db.ts";
import { freshness } from "../../../../lib/claude.tsx";
import { blocksOf, MessageCard, ResponseCard, type Msg } from "../../../../lib/gateway.tsx";

export const dynamic = "force-dynamic";

/** One conversation through the door, read like a chat: each relayed turn shows
 *  the DELTA the caller added (the last message of its request — the rest is
 *  history resent) and the answer that came back. The full raw turn is one
 *  click deeper. */
export default async function GatewaySessionPage({
  params,
}: {
  params: Promise<{ session: string }>;
}) {
  const { session } = await params;
  const turns = await gatewaySession(session);

  if (turns.length === 0) {
    return (
      <Shell active="~gateway">
        <h1>gateway</h1>
        <p className="empty">no session <code>{session}</code> in the log.</p>
      </Shell>
    );
  }

  const last = turns[turns.length - 1];

  return (
    <Shell active="~gateway">
      <h1>one conversation through the door</h1>
      <p className="sub">
        <Link href="/gateway">← gateway</Link> · <code>{session}</code> ·{" "}
        {last.model ?? "—"} · {turns.length} turns · {freshness(last.ts)}
      </p>
      {turns.map((t) => {
        const msg = (t.last_msg ?? {}) as Msg;
        return (
          <div key={t.exchange}>
            <MessageCard role={msg.role} blocks={blocksOf(msg.content)} />
            <ResponseCard
              model={t.model}
              content={t.answer}
              stopReason={t.stop_reason}
              inputTokens={t.input_tokens}
              outputTokens={t.output_tokens}
              href={`/gateway/${t.exchange}`}
            />
          </div>
        );
      })}
    </Shell>
  );
}
