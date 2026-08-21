import Link from "next/link";
import Shell from "../../components/Shell.tsx";
import { gatewaySessions, gatewayTurns } from "../../lib/db.ts";
import { freshness } from "../../lib/claude.tsx";

export const dynamic = "force-dynamic";

/** The gateway door's memory, grouped the way /claude groups a casita: one row
 *  per CONVERSATION (the session id the caller sent), loose one-shot exchanges
 *  below. What crossed the wire, read straight from aire_gateway_log. */
export default async function GatewayPage() {
  const [sessions, loose] = await Promise.all([gatewaySessions(), gatewayTurns()]);

  return (
    <Shell active="~gateway">
      <h1>gateway</h1>
      <p className="sub">
        every turn relayed through the door, grouped by the caller&apos;s
        <code> session</code> — read straight from <code>aire_gateway_log</code>.
      </p>

      <h2 className="sect">conversations · {sessions.length}</h2>
      {sessions.length === 0 ? (
        <p className="empty">no session has come through the gateway yet.</p>
      ) : (
        <div className="panel">
          <table>
            <thead>
              <tr>
                <th>last activity</th>
                <th>asked</th>
                <th>app</th>
                <th>key</th>
                <th>model</th>
                <th>turns</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.session_id}>
                  <td>
                    <Link href={`/gateway/s/${s.session_id}`}>{freshness(s.ts)}</Link>
                  </td>
                  <td>{s.asked ? s.asked : <span className="empty">—</span>}</td>
                  <td>{s.project ?? "—"}</td>
                  <td>{s.holder ?? "—"}</td>
                  <td>{s.model ?? "—"}</td>
                  <td>{s.turns.toLocaleString("en-US")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2 className="sect">loose exchanges · {loose.length}</h2>
      {loose.length === 0 ? (
        <p className="empty">every exchange arrived with a session id.</p>
      ) : (
        <div className="panel">
          <table>
            <thead>
              <tr>
                <th>when</th>
                <th>asked</th>
                <th>key</th>
                <th>model</th>
                <th>stop</th>
                <th>in</th>
                <th>out</th>
              </tr>
            </thead>
            <tbody>
              {loose.map((t) => (
                <tr key={t.exchange}>
                  <td>
                    <Link href={`/gateway/${t.exchange}`}>{freshness(t.ts)}</Link>
                  </td>
                  <td>{t.asked ? t.asked : <span className="empty">—</span>}</td>
                  <td>{t.holder ?? "—"}</td>
                  <td>{t.model ?? "—"}</td>
                  <td>{t.stop_reason ?? (t.status ? `HTTP ${t.status}` : "…")}</td>
                  <td>{t.input_tokens?.toLocaleString("en-US") ?? "—"}</td>
                  <td>{t.output_tokens?.toLocaleString("en-US") ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Shell>
  );
}
