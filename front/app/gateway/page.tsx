import Link from "next/link";
import Shell from "../../components/Shell.tsx";
import { gatewayTurns } from "../../lib/db.ts";
import { freshness } from "../../lib/claude.tsx";

export const dynamic = "force-dynamic";

/** The gateway door's memory: one row per relayed turn. `/claude` shows what the
 *  agent remembered; this shows what actually crossed the wire — the raw API
 *  exchange of every app pointed at AIRE by env var. */
export default async function GatewayPage() {
  const turns = await gatewayTurns();

  return (
    <Shell active="~gateway">
      <h1>gateway</h1>
      <p className="sub">
        every turn relayed through the door, request and response paired by
        <code> exchange</code> — read straight from <code>aire_gateway_log</code>.
      </p>
      {turns.length === 0 ? (
        <p className="empty">nothing has come through the gateway yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>when</th>
              <th>asked</th>
              <th>model</th>
              <th>stop</th>
              <th>in</th>
              <th>out</th>
            </tr>
          </thead>
          <tbody>
            {turns.map((t) => (
              <tr key={t.exchange}>
                <td>
                  <Link href={`/gateway/${t.exchange}`}>{freshness(t.ts)}</Link>
                </td>
                <td>{t.asked ? t.asked : <span className="empty">—</span>}</td>
                <td>{t.model ?? "—"}</td>
                <td>{t.stop_reason ?? (t.status ? `HTTP ${t.status}` : "…")}</td>
                <td>{t.input_tokens?.toLocaleString("en-US") ?? "—"}</td>
                <td>{t.output_tokens?.toLocaleString("en-US") ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Shell>
  );
}
