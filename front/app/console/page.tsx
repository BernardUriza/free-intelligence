import Link from "next/link";
import Shell from "../../components/Shell.tsx";
import { claudeRecent, gatewayCounts, gatewaySessions, lastBreath, tables, where } from "../../lib/db.ts";
import { folderName, sessionTitle, When } from "../../lib/claude.tsx";
import { readable } from "../../lib/gateway.tsx";

export const dynamic = "force-dynamic";

/**
 * The overview — EC-GPS's PHP console, first screen, asking the question a
 * reader actually arrives with: what has AIRE remembered lately?
 *
 * It used to open on `7 tables, 5,280 rows`. That is true and it is the wrong
 * first sentence: it describes the storage instead of the memory. The tiles
 * below count conversations; the table sizes moved to the bottom, where the
 * plumbing belongs.
 */
export default async function Overview() {
  const { host, database } = where();

  let list, recent, gw, sessions, breath;
  try {
    [list, recent, gw, sessions, breath] = await Promise.all([
      tables(),
      claudeRecent(8),
      gatewayCounts(),
      gatewaySessions(6),
      lastBreath(),
    ]);
  } catch (err) {
    return (
      <Shell active="~console">
        <h1>The database is unreachable</h1>
        <p className="sub">The waiter cannot read what it cannot reach.</p>
        <div className="err">{err instanceof Error ? err.message : String(err)}</div>
      </Shell>
    );
  }

  const rowsOf = (name: string) => list.find((t) => t.name === name)?.rows ?? 0;
  const folders = new Set(recent.map((r) => r.project_key));

  return (
    <Shell active="~console">
      <h1>
        overview
        <span className="ro">read only</span>
      </h1>
      <p className="sub">
        Everything the daemon has written, as this console can see it. The pen is in{" "}
        <code>aire-server</code>; this page never writes. — <code>{database}</code> at{" "}
        {host}
      </p>

      <div className="tiles">
        <Link className="tile" href="/claude">
          <span className="k">mirrored entries</span>
          <span className="v">{rowsOf("claude_session_store").toLocaleString("en-US")}</span>
          <span className="u">transcript lines the SDK carried out</span>
        </Link>
        <Link className="tile" href="/gateway">
          <span className="k">turns relayed</span>
          <span className="v">{gw.requests.toLocaleString("en-US")}</span>
          <span className="u">
            {gw.sessions.toLocaleString("en-US")} conversation
            {gw.sessions === 1 ? "" : "s"} through the door
          </span>
        </Link>
        <Link className="tile" href="/monster">
          <span className="k">events on the port</span>
          <span className="v">{rowsOf("aire_log").toLocaleString("en-US")}</span>
          <span className="u">lines the listener appended</span>
        </Link>
        <div className="tile">
          <span className="k">last breath</span>
          <span className="v" style={{ fontSize: 19 }}>
            <When mtime={breath} />
          </span>
          <span className="u">the newest line in the log</span>
        </div>
      </div>

      <h2 className="sect">
        <span>latest conversations</span>
        <Link className="more" href="/claude">
          all {folders.size > 0 ? "folders" : ""} →
        </Link>
      </h2>
      {recent.length === 0 ? (
        <div className="panel">
          <p className="empty">no conversation has been mirrored yet.</p>
        </div>
      ) : (
        <div className="panel">
          <div className="scroll">
            <table>
              <thead>
                <tr>
                  <th>session</th>
                  <th>folder</th>
                  <th className="num">entries</th>
                  <th>last activity</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((s) => (
                  <tr key={s.session_id}>
                    <td className="said name">
                      <Link href={`/claude/${encodeURIComponent(s.project_key)}/${s.session_id}`}>
                        {s.ai_title ?? sessionTitle(s.first_user)}
                      </Link>
                    </td>
                    <td>
                      <Link href={`/claude/${encodeURIComponent(s.project_key)}`}>
                        {folderName(s.project_key)}
                      </Link>
                    </td>
                    <td className="num">{s.entries}</td>
                    <td>
                      <When mtime={s.mtime} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <h2 className="sect">
        <span>latest through the gateway</span>
        <Link className="more" href="/gateway">
          all →
        </Link>
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
                  <th>model</th>
                  <th className="num">turns</th>
                  <th>last activity</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.session_id}>
                    <td className="said name">
                      <Link href={`/gateway/s/${s.session_id}`}>
                        {readable(s.asked) || "—"}
                      </Link>
                    </td>
                    <td>{s.project ?? "—"}</td>
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

      <h2 className="sect">
        <span>raw tables · {list.length}</span>
      </h2>
      <div className="panel">
        <div className="scroll">
          <table>
            <thead>
              <tr>
                <th>table</th>
                <th className="num">rows</th>
                <th className="num">size</th>
              </tr>
            </thead>
            <tbody>
              {list.map((t) => (
                <tr key={t.name}>
                  <td className="name">
                    <Link href={`/t/${t.name}`}>{t.name}</Link>
                  </td>
                  <td className="num">{t.rows.toLocaleString("en-US")}</td>
                  <td className="num">{t.size}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Shell>
  );
}
