import Shell from "../../components/Shell.tsx";
import { Cell } from "../../lib/cell.tsx";
import { console_ } from "../../lib/db.ts";

export const dynamic = "force-dynamic";

/**
 * The SQL console — phpMyAdmin's heart.
 *
 * A plain GET form, so a query is a URL you can bookmark and share, and the page
 * needs not one byte of client JavaScript. That is only safe because every
 * statement it can run is a read: the four walls in `lib/db.ts` see to that, and
 * `scripts/attack.ts` proves it against the real database on every change.
 */
export default async function SqlPage({
  searchParams,
}: {
  searchParams: Promise<{ sql?: string }>;
}) {
  const { sql = "" } = await searchParams;
  const statement = sql.trim();

  let headers: string[] = [];
  let rows: Record<string, unknown>[] = [];
  let error = "";

  if (statement) {
    try {
      ({ headers, rows } = await console_(statement));
    } catch (err) {
      error = err instanceof Error ? `${err.name}: ${err.message}` : String(err);
    }
  }

  return (
    <Shell active="~sql">
      <h1>
        SQL console<span className="ro">read only</span>
      </h1>
      <p className="sub">
        Type anything. A write does not need to be caught by a sanitizer here — the statement
        never begins a write, the transaction is opened <code>READ ONLY</code>, and only one
        statement crosses the wire. Try <code>DELETE FROM aire_log</code> and watch it bounce.
      </p>

      <form method="get" action="/sql">
        <textarea
          name="sql"
          defaultValue={statement}
          placeholder="SELECT * FROM aire_log ORDER BY seq DESC LIMIT 20"
        />
        <div className="bar" style={{ marginTop: 10 }}>
          <button>Run</button>
        </div>
      </form>

      {error && <div className="err">{error}</div>}

      {!error && statement && rows.length === 0 && (
        <div className="panel">
          <div className="empty">The query returned no rows.</div>
        </div>
      )}

      {!error && rows.length > 0 && (
        <div className="panel">
          <table>
            <thead>
              <tr>
                {headers.map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  {headers.map((h) => (
                    <Cell key={h} value={row[h]} />
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Shell>
  );
}
