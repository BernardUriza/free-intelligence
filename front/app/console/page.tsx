import Link from "next/link";
import Shell from "../../components/Shell.tsx";
import { tables, where } from "../../lib/db.ts";

export const dynamic = "force-dynamic";

/** The index — what the daemon has written. EC-GPS's PHP console, first screen. */
export default async function Home() {
  const { host, database } = where();

  let list;
  try {
    list = await tables();
  } catch (err) {
    return (
      <Shell>
        <h1>The database is unreachable</h1>
        <p className="sub">The waiter cannot read what it cannot reach.</p>
        <div className="err">{err instanceof Error ? err.message : String(err)}</div>
      </Shell>
    );
  }

  if (list.length === 0) {
    return (
      <Shell>
        <h1>Nothing written yet</h1>
        <p className="sub">
          The database is empty — the daemon has not appended a single row.
        </p>
      </Shell>
    );
  }

  const total = list.reduce((sum, t) => sum + t.rows, 0);

  return (
    <Shell>
      <h1>
        {database}
        <span className="ro">read only</span>
      </h1>
      <p className="sub">
        What the daemon has written — {list.length} table{list.length === 1 ? "" : "s"},{" "}
        {total.toLocaleString("en-US")} rows. The pen is in <code>aire-server</code>; this
        page never writes.
        <br />
        {host}
      </p>
      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>table</th>
              <th>rows</th>
              <th>size</th>
            </tr>
          </thead>
          <tbody>
            {list.map((t) => (
              <tr key={t.name}>
                <td>
                  <Link href={`/t/${t.name}`}>{t.name}</Link>
                </td>
                <td>{t.rows.toLocaleString("en-US")}</td>
                <td>{t.size}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
