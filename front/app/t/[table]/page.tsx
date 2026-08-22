import Link from "next/link";
import Shell from "../../../components/Shell.tsx";
import { Cell } from "../../../lib/cell.tsx";
import { browse, UnknownTable } from "../../../lib/db.ts";

export const dynamic = "force-dynamic";

type Search = { order?: string; desc?: string; limit?: string; offset?: string; q?: string };

/** Browse a table: paginate it, sort it, search every text column. The table name
 *  arrives from the URL and is validated against the live catalog inside `browse`
 *  — an unknown name throws before it can be quoted into SQL. */
export default async function TablePage({
  params,
  searchParams,
}: {
  params: Promise<{ table: string }>;
  searchParams: Promise<Search>;
}) {
  const { table } = await params;
  const sp = await searchParams;

  const limit = Math.min(Math.max(Number(sp.limit) || 50, 1), 500);
  const offset = Math.max(Number(sp.offset) || 0, 0);
  const desc = sp.desc !== "0";
  const q = sp.q ?? "";

  let page;
  try {
    page = await browse(table, { limit, offset, order: sp.order, desc, q });
  } catch (err) {
    if (err instanceof UnknownTable) {
      return (
        <Shell>
          <h1>No such table</h1>
          <p className="sub">
            The catalog does not report <code>{err.message}</code>.
          </p>
        </Shell>
      );
    }
    throw err;
  }

  const { cols, rows, total, order } = page;
  const base = `/t/${table}?order=${order}&desc=${desc ? "1" : "0"}&limit=${limit}&q=${encodeURIComponent(q)}`;
  const shown = total > 0 ? `${(offset + 1).toLocaleString("en-US")}–${Math.min(offset + limit, total).toLocaleString("en-US")} of ${total.toLocaleString("en-US")}` : "0";

  return (
    <Shell active={table}>
      <h1>
        <code>{table}</code>
        <span className="ro">read only</span>
      </h1>
      <p className="sub">
        A raw table, as the daemon wrote it — {cols.length} columns ·{" "}
        {total.toLocaleString("en-US")} rows.
      </p>

      <div className="bar">
        <form method="get" action={`/t/${table}`}>
          <input type="hidden" name="order" value={order} />
          <input type="hidden" name="desc" value={desc ? "1" : "0"} />
          <input type="text" name="q" defaultValue={q} placeholder="search every text column…" />
          <button>Search</button>
        </form>
        <span className="page">
          {shown}
          {offset > 0 && <Link href={`${base}&offset=${Math.max(0, offset - limit)}`}>← prev</Link>}
          {offset + limit < total && <Link href={`${base}&offset=${offset + limit}`}>next →</Link>}
        </span>
      </div>

      <div className="panel">
        {rows.length === 0 ? (
          <div className="empty">No rows{q ? ` match “${q}”` : ""}.</div>
        ) : (
          <div className="scroll">
          <table>
            <thead>
              <tr>
                {cols.map((c) => {
                  const flip = c.name === order && desc ? "0" : "1";
                  const arrow = c.name === order ? (desc ? " ▾" : " ▴") : "";
                  return (
                    <th key={c.name}>
                      <Link href={`/t/${table}?order=${c.name}&desc=${flip}&limit=${limit}&q=${encodeURIComponent(q)}`}>
                        {c.name}
                      </Link>
                      <span className="dir">{arrow}</span>
                      <br />
                      <span className="type">{c.type}</span>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  {cols.map((c) => (
                    <Cell key={c.name} value={row[c.name]} />
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>
    </Shell>
  );
}
