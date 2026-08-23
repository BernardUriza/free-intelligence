import Link from "next/link";
import Shell from "../../components/Shell.tsx";
import { gatewaySessions, gatewayTurns } from "../../lib/db.ts";
import { When } from "../../lib/claude.tsx";
import { readable } from "../../lib/gateway.tsx";

export const dynamic = "force-dynamic";

/** The gateway door's memory, grouped the way /claude groups a casita: one row
 *  per CONVERSATION (the session id the caller sent), loose one-shot exchanges
 *  below. What crossed the wire, read straight from aire_gateway_log. */
const PAGE = 60;

export default async function GatewayPage(
  { searchParams }: { searchParams: Promise<{ before?: string; looseBefore?: string }> },
) {
  const { before, looseBefore } = await searchParams;
  const [sessions, loose] = await Promise.all([
    gatewaySessions(PAGE, before),
    gatewayTurns(PAGE, looseBefore),
  ]);
  // The cursor is the last row's own seq, so "older" asks for what sits below
  // this page. A full page means there is probably more; a short one is the end.
  const olderSessions = sessions.length === PAGE
    ? `?before=${sessions[sessions.length - 1].last_seq}${looseBefore ? `&looseBefore=${looseBefore}` : ""}`
    : null;
  const olderLoose = loose.length === PAGE
    ? `?looseBefore=${loose[loose.length - 1].seq}${before ? `&before=${before}` : ""}`
    : null;

  return (
    <Shell active="~gateway">
      <h1>gateway</h1>
      <p className="sub">
        Every turn relayed through the door, grouped by the caller&apos;s{" "}
        <code>session</code> — read straight from <code>aire_gateway_log</code>. The
        preview is what the human said, with the scaffolding the client sent taken off
        the front.
      </p>

      <h2 className="sect">
        <span>conversations · {sessions.length}</span>
        {before ? <Link href="/gateway">newest</Link> : null}
      </h2>
      {sessions.length === 0 ? (
        <div className="panel">
          <p className="empty">no session has come through the gateway yet.</p>
        </div>
      ) : (
        <div className="panel">
          <div className="scroll">
            <table>
              <thead>
                <tr>
                  <th>asked</th>
                  <th>app</th>
                  <th>key</th>
                  <th>model</th>
                  <th className="num">turns</th>
                  <th>last activity</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.session_id}>
                    <td className="said name">
                      <Link href={`/gateway/s/${s.session_id}`}>{readable(s.asked) || "—"}</Link>
                    </td>
                    <td>{s.project ?? "—"}</td>
                    <td>{s.holder ?? "—"}</td>
                    <td>{s.model ?? "—"}</td>
                    <td className="num">{s.turns.toLocaleString("en-US")}</td>
                    <td>
                      <When mtime={s.ts} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {olderSessions ? (
        <p className="sub">
          <Link href={`/gateway${olderSessions}`}>older conversations →</Link>
        </p>
      ) : null}

      <h2 className="sect">
        <span>loose exchanges · {loose.length}</span>
        {looseBefore ? <Link href="/gateway">newest</Link> : null}
      </h2>
      {loose.length === 0 ? (
        <div className="panel">
          <p className="empty">every exchange arrived with a session id.</p>
        </div>
      ) : (
        <div className="panel">
          <div className="scroll">
            <table>
              <thead>
                <tr>
                  <th>asked</th>
                  <th>key</th>
                  <th>model</th>
                  <th>stop</th>
                  <th className="num">in</th>
                  <th className="num">out</th>
                  <th>when</th>
                </tr>
              </thead>
              <tbody>
                {loose.map((t) => (
                  <tr key={t.exchange}>
                    <td className="said name">
                      <Link href={`/gateway/${t.exchange}`}>{readable(t.asked) || "—"}</Link>
                    </td>
                    <td>{t.holder ?? "—"}</td>
                    <td>{t.model ?? "—"}</td>
                    <td>{t.stop_reason ?? (t.status ? `HTTP ${t.status}` : "…")}</td>
                    <td className="num">{t.input_tokens?.toLocaleString("en-US") ?? "—"}</td>
                    <td className="num">{t.output_tokens?.toLocaleString("en-US") ?? "—"}</td>
                    <td>
                      <When mtime={t.ts} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {olderLoose ? (
        <p className="sub">
          <Link href={`/gateway${olderLoose}`}>older exchanges →</Link>
        </p>
      ) : null}
    </Shell>
  );
}
