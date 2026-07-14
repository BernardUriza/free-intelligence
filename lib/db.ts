/**
 * The waiter's hands — the only module that touches Postgres, and it may only read.
 *
 * The daemon (`aire-server`) holds the pen; this repo holds the menu. That
 * separation is not enforced by good intentions: it is enforced four times over,
 * because on 2026-07-13 a version of this file that enforced it only ONCE was
 * defeated in about a minute, and a row of garbage landed in the production log.
 *
 * What defeated it: `default_transaction_read_only` is a *default*, not a lock.
 * The `aire` role owns write privileges, so a plain `SET TRANSACTION READ WRITE`
 * takes them straight back and every write after it goes through. Verified, not
 * reasoned about — see `scripts/attack.ts`, which re-runs the whole assault.
 *
 * And node-postgres makes it WORSE than the Python driver did: `pg` speaks the
 * simple query protocol when a query carries no parameters, and the simple
 * protocol happily runs `SET TRANSACTION READ WRITE; DELETE FROM aire_log` as
 * one round trip. What asyncpg refused for free, `pg` hands to an attacker.
 *
 * Hence four walls, each covering the previous one's hole:
 *
 *   1. `default_transaction_read_only=on` on the connection.
 *   2. an explicit `BEGIN … READ ONLY` around the statement.
 *   3. the extended query protocol (always pass `values`), so ONE statement per
 *      round trip — this is what kills the `SET …; DELETE …` combo.
 *   4. the statement must BEGIN a read — no `SET`, so walls 1 and 2 cannot be
 *      disarmed in the first place.
 *
 * None of this is the real fix. The real fix is a credential that CANNOT write:
 * role `aire_reader`, `GRANT SELECT`, nothing else. Then `SET TRANSACTION READ
 * WRITE` buys an attacker precisely nothing and these four walls become the belt
 * behind the braces. It needs the Postgres server admin — see the backlog.
 */

import { Pool, type PoolClient } from "pg";

const READS_ONLY = /^\s*(?:select|with|explain|table|values|show)\b/i;

// The `name` is set explicitly because the production build MINIFIES class names:
// `err.constructor.name` renders as `n` once Turbopack is done with it, and the
// console was reporting "n: This console only runs reads…" to the user.
export class NotARead extends Error {
  override name = "NotARead";
}
export class UnknownTable extends Error {
  override name = "UnknownTable";
}

export type Table = { name: string; rows: number; size: string };
export type Column = { name: string; type: string; nullable: boolean };

const TEXTUAL = new Set([
  "text",
  "character varying",
  "character",
  "uuid",
  "jsonb",
  "json",
]);

declare global {
  var __airePool: Pool | undefined;
}

/** Wall 1 — `options` rides in the startup packet, so every connection in the
 *  pool is born read-only by default. */
export function pool(): Pool {
  if (!globalThis.__airePool) {
    const connectionString = process.env.AIRE_DATABASE_URL;
    if (!connectionString) {
      throw new Error("AIRE_DATABASE_URL is not set — the waiter has nothing to read.");
    }
    const local = /@(localhost|127\.0\.0\.1)[:/]/.test(connectionString);
    globalThis.__airePool = new Pool({
      connectionString,
      options: "-c default_transaction_read_only=on",
      max: 4,
      // `sslmode=require` in the DSN means "encrypt" but NOT "check who you are
      // talking to" — pg's legacy default accepts any certificate, which is a
      // MITM waiting to happen against a database on the public internet. Azure
      // Postgres presents a DigiCert chain that Node's trust store already knows,
      // so demanding a valid one costs nothing and closes the hole.
      ssl: local ? undefined : { rejectUnauthorized: true },
    });
  }
  return globalThis.__airePool;
}

/** Walls 2 + 3 — every read this app makes goes through here, inside a
 *  transaction that BEGAN read-only, over the extended protocol (note the
 *  always-present `values`: that is what forbids a second statement). */
async function read<T = Record<string, unknown>>(
  sql: string,
  values: unknown[] = [],
): Promise<T[]> {
  const client: PoolClient = await pool().connect();
  try {
    await client.query("BEGIN READ ONLY");
    const result = await client.query({ text: sql, values });
    await client.query("COMMIT");
    return result.rows as T[];
  } catch (err) {
    await client.query("ROLLBACK").catch(() => {});
    throw err;
  } finally {
    client.release();
  }
}

/** Postgres-quote an identifier the catalog has already vouched for. The catalog
 *  check upstream is what makes this safe — this escape is the second lock. */
function quote(identifier: string): string {
  return '"' + identifier.replace(/"/g, '""') + '"';
}

/**
 * Every base table in `public`, heaviest first — the daemon's DDL as the database
 * actually holds it, not as some model in this repo imagines it. A table the
 * daemon adds tomorrow (`claude_session_store`) shows up here with no code change:
 * that is the whole point of reading the catalog instead of hardcoding a schema.
 */
export async function tables(): Promise<Table[]> {
  const listed = await read<{ name: string; size: string }>(`
    SELECT c.relname AS name,
           pg_size_pretty(pg_total_relation_size(c.oid)) AS size
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind = 'r'
    ORDER BY pg_total_relation_size(c.oid) DESC, c.relname
  `);

  const out: Table[] = [];
  for (const { name, size } of listed) {
    const [{ count }] = await read<{ count: string }>(
      `SELECT count(*)::text AS count FROM public.${quote(name)}`,
    );
    out.push({ name, size, rows: Number(count) });
  }
  return out;
}

export async function columns(table: string): Promise<Column[]> {
  const found = await read<{
    column_name: string;
    data_type: string;
    is_nullable: string;
  }>(
    `SELECT column_name, data_type, is_nullable
     FROM information_schema.columns
     WHERE table_schema = 'public' AND table_name = $1
     ORDER BY ordinal_position`,
    [table],
  );
  if (found.length === 0) throw new UnknownTable(table);
  return found.map((c) => ({
    name: c.column_name,
    type: c.data_type,
    nullable: c.is_nullable === "YES",
  }));
}

export type Page = {
  cols: Column[];
  rows: Record<string, unknown>[];
  total: number;
  order: string;
};

/** One page of a table. `order` and the searched columns are checked against the
 *  live catalog before they are quoted — an unknown name throws instead of
 *  reaching SQL. */
export async function browse(
  table: string,
  opts: { limit?: number; offset?: number; order?: string; desc?: boolean; q?: string } = {},
): Promise<Page> {
  const { limit = 50, offset = 0, desc = true, q = "" } = opts;
  const cols = await columns(table);
  const names = new Set(cols.map((c) => c.name));

  const order = opts.order ?? cols[0].name;
  if (!names.has(order)) throw new UnknownTable(order);

  const relation = `public.${quote(table)}`;
  const values: unknown[] = [];
  let where = "";
  if (q) {
    const searchable = cols.filter((c) => TEXTUAL.has(c.type));
    if (searchable.length > 0) {
      const haystack = searchable
        .map((c) => `coalesce(${quote(c.name)}::text, '')`)
        .join(" || ' ' || ");
      values.push(`%${q}%`);
      where = `WHERE ${haystack} ILIKE $1`;
    }
  }

  const [{ count }] = await read<{ count: string }>(
    `SELECT count(*)::text AS count FROM ${relation} ${where}`,
    values,
  );
  const rows = await read(
    `SELECT * FROM ${relation} ${where}
     ORDER BY ${quote(order)} ${desc ? "DESC" : "ASC"}
     LIMIT ${Math.trunc(limit)} OFFSET ${Math.trunc(offset)}`,
    values,
  );
  return { cols, rows, total: Number(count), order };
}

/**
 * The SQL console — phpMyAdmin's heart, and the reason the walls live in the
 * engine rather than in a sanitizer. Whatever is typed, the database refuses to
 * write it: `DELETE FROM aire_log` reaches Postgres and Postgres says no.
 *
 * Wall 4 lives here. It is not decoration: it is the wall that stops `SET
 * TRANSACTION READ WRITE`, without which walls 1 and 2 can be switched off by
 * the very SQL they are supposed to contain.
 */
export async function console_(sql: string, limit = 200) {
  if (!READS_ONLY.test(sql)) {
    throw new NotARead(
      "This console only runs reads — SELECT, WITH, EXPLAIN, TABLE, VALUES, SHOW. " +
        "Not because writing would be inconvenient: the transcript is append-only, " +
        "and the pen lives in aire-server.",
    );
  }
  const rows = await read(sql);
  const trimmed = rows.slice(0, limit);
  return { headers: trimmed.length > 0 ? Object.keys(trimmed[0]) : [], rows: trimmed };
}

/** The monster's feed. Kept here so `db` stays the only module holding a cursor —
 *  the DFG view derives, it does not connect. */
export async function logLines(): Promise<{ seq: number; line: string }[]> {
  const rows = await read<{ seq: string; line: string }>(
    "SELECT seq, line FROM aire_log ORDER BY seq",
  );
  return rows.map((r) => ({ seq: Number(r.seq), line: r.line }));
}

export function where(): { host: string; database: string } {
  try {
    const url = new URL(process.env.AIRE_DATABASE_URL ?? "");
    return { host: url.hostname, database: url.pathname.replace(/^\//, "") || "?" };
  } catch {
    return { host: "?", database: "?" };
  }
}
