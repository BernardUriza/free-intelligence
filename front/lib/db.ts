/**
 * The waiter's hands — the only module that touches Postgres, and it may only read.
 *
 * The daemon (`aire-server`) holds the pen; this repo holds the menu.
 *
 * THE WALL IS THE CREDENTIAL. The app connects as `aire_reader`: a role holding
 * `GRANT SELECT` and nothing else, so there is no write privilege for anyone to
 * re-enable. `scripts/attack.ts` refuses to run at all unless it arrived as such a
 * role — hand this app the daemon's credential and the suite stops dead rather
 * than printing a comforting wall of "blocked".
 *
 * The four walls below are DEFENCE IN DEPTH, not the defence. They exist because
 * the first version of this file had ONLY them, and they fell in about a minute:
 * `default_transaction_read_only` is a *default*, not a lock, and the pen's role
 * took the privilege straight back with `SET TRANSACTION READ WRITE`. A row of
 * garbage reached the production log and is still there (`aire_log`, seq 2641) —
 * append-only means the scar stays too.
 *
 *   1. `default_transaction_read_only=on` on the connection.
 *   2. an explicit `BEGIN … READ ONLY` around the statement.
 *   3. the extended query protocol (always pass `values`), so ONE statement per
 *      round trip — node-postgres speaks the SIMPLE protocol when a query carries
 *      no parameters, and the simple protocol runs `SET …; DELETE …` as one round
 *      trip. What asyncpg refused for free, `pg` hands to an attacker.
 *   4. the statement must BEGIN a read — no `SET`, so walls 1 and 2 cannot be
 *      disarmed in the first place.
 *
 * And a fifth thing that is not about writes at all: `statement_timeout`. Wall 4
 * only checks that a statement *begins* a read, so `SELECT pg_sleep(3600)` sails
 * through it — and with `max: 4`, four of those freeze the WHOLE app (every page
 * needs a connection for the sidebar), not just the console. A runaway `ORDER BY`
 * over a million rows does the same thing without any malice at all.
 */

import { cache } from "react";
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
      // `statement_timeout` is not paranoia, it is the difference between a slow
      // page and a dead app: `SELECT pg_sleep(3600)` passes wall 4 (it *begins* a
      // read), holds a connection, and four of them exhaust `max`. Postgres kills
      // the query and hands the connection back instead.
      options: "-c default_transaction_read_only=on -c statement_timeout=15000",
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
 *
 * Wrapped in React's `cache()` because EVERY page renders `<Shell>`, which needs
 * this list for the sidebar — and the page itself may want it too. Without the
 * dedupe, `/` ran the whole thing TWICE per request, and each run is a `count(*)`
 * per table: two full scans of a log that grows by 2,500 rows an hour. `cache()`
 * collapses them to one call per request; the next request gets fresh numbers.
 */
export const tables = cache(async function tables(): Promise<Table[]> {
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
});

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

export type Graph = {
  nodes: { name: string; count: number }[];
  edges: { from: string; to: string; count: number }[];
  total: number;
  span: string;
  /** Rows the graph actually looked at, and whether that was the whole log. A
   *  window that is not shown to the reader is a lie about what they are seeing. */
  scanned: number;
  windowed: boolean;
};

/** The monster reads the tail of the log, not all of it. At 6.3 µs/row the whole
 *  scan stays under `statement_timeout` until roughly 2.4M rows — which the log
 *  reaches in about 40 days — and a graph of "everything since the beginning of
 *  time" is not more informative than a graph of the recent past anyway: it just
 *  averages away the era you actually care about. Bounded, predictable, honest. */
export const MONSTER_WINDOW = 200_000;

/**
 * The monster's directly-follows graph — **counted in Postgres, not in Node.**
 *
 * The first version pulled every row of `aire_log` into memory and folded it in
 * JavaScript. Measured, not guessed: 413 bytes of heap per row, against a log
 * growing 2,493 rows/hour. At thirty days that is 1.8M rows → **709 MB of heap in
 * a 1 GB container, and 235 seconds per page view** — before `buildGraph`
 * allocated a second array of 1.8M strings on top. The page was a scheduled OOM.
 *
 * The database was always the right place to count. `lead()` over the classified
 * events gives every "B followed A" pair and `GROUP BY` collapses them: what
 * crosses the wire is ~50 aggregate rows no matter how large the log gets.
 *
 * **That fixed the memory and left the clock.** The obvious classifier — one regex
 * with lookahead per line — cost 98 µs/row, so the scan would have blown
 * `statement_timeout` at ~153k rows: SIXTY-ONE HOURS away. Moving the work to SQL
 * without measuring it would have shipped the same bomb with a shorter fuse.
 *
 * So the classifier takes the format seriously. The daemon writes
 * `TS IP:PORT app EVENT [SUBTYPE] …`, which means the event is **token 4** — two
 * anchored regexes on short tokens instead of one lookahead across the whole line.
 * 6.3 µs/row, a **15× speedup**, verified identical to the slow path on the live
 * log (same nodes, same edges, same counts). Lines that do NOT follow the format
 * (garbage arriving on the open port — 36 rows out of 7,800) fall through to the
 * slow regex, so nothing is lost; they are simply too rare to pay for.
 *
 * Bonus the move buys for free: the edge arrives as two COLUMNS, `a` and `b`. The
 * old code packed `from` and `to` into one map key and split it apart again — with
 * a separator that had to be a NUL byte, because node names contain spaces
 * (`MESSAGE POS`). It worked, and it was invisible: every editor rendered that NUL
 * as an ordinary space, one keystroke from silently breaking every `MESSAGE *` edge.
 */
export async function graph(): Promise<Graph> {
  const rows = await read<{ shape: string; a: string | null; b: string | null; n: string }>(
    `
    WITH windowed AS (
      SELECT seq, line FROM aire_log ORDER BY seq DESC LIMIT $1
    ),
    parsed AS (
      SELECT seq, line,
             split_part(line, ' ', 4) AS t4,
             split_part(line, ' ', 5) AS t5
      FROM windowed
    ),
    classified AS (
      SELECT seq,
        CASE
          WHEN t4 ~ '^[A-Z][A-Z0-9-]*$'
           AND split_part(line, ' ', 2) !~ '^[A-Z][A-Z0-9-]*$'
           AND split_part(line, ' ', 3) !~ '^[A-Z][A-Z0-9-]*$'
            THEN CASE WHEN t4 = 'MESSAGE' AND t5 ~ '^[A-Z][A-Z0-9-]*$'
                      THEN 'MESSAGE ' || t5
                      ELSE t4 END
          ELSE (
            SELECT CASE
                     WHEN m IS NULL THEN
                       CASE WHEN array_length(regexp_split_to_array(btrim(line), '\\s+'), 1) > 2
                            THEN 'OTHER' END
                     WHEN m[1] = 'MESSAGE' AND m[2] IS NOT NULL THEN 'MESSAGE ' || m[2]
                     ELSE m[1]
                   END
            FROM (
              SELECT regexp_match(line,
                '(?:^|\\s)([A-Z][A-Z0-9-]*)(?=\\s|$)(?:\\s([A-Z][A-Z0-9-]*)(?=\\s|$))?') AS m
            ) z
          )
        END AS kind
      FROM parsed
    ),
    events AS (SELECT seq, kind FROM classified WHERE kind IS NOT NULL),
    pairs  AS (SELECT kind AS a, lead(kind) OVER (ORDER BY seq) AS b FROM events)
    SELECT 'node' AS shape, kind AS a, NULL::text AS b, count(*)::text AS n
      FROM events GROUP BY kind
    UNION ALL
    SELECT 'edge', a, b, count(*)::text
      FROM pairs WHERE b IS NOT NULL GROUP BY a, b
    UNION ALL
    SELECT 'meta', NULL, NULL, count(*)::text FROM windowed
    `,
    [MONSTER_WINDOW],
  );

  const nodes = rows
    .filter((r) => r.shape === "node")
    .map((r) => ({ name: r.a as string, count: Number(r.n) }))
    .sort((x, y) => y.count - x.count);

  const edges = rows
    .filter((r) => r.shape === "edge")
    .map((r) => ({ from: r.a as string, to: r.b as string, count: Number(r.n) }));

  const scanned = Number(rows.find((r) => r.shape === "meta")?.n ?? 0);
  const total = nodes.reduce((sum, n) => sum + n.count, 0);

  // The span is the log's own text, not `at`, so it reads exactly as the daemon
  // wrote it — and it describes THE WINDOW, not the log, or the page would claim
  // to show a history it never looked at. Two index lookups, not a scan.
  const [ends] = await read<{ first: string | null; last: string | null }>(
    `
    WITH windowed AS (SELECT seq, line FROM aire_log ORDER BY seq DESC LIMIT $1)
    SELECT (SELECT split_part(line, ' ', 1) FROM windowed ORDER BY seq ASC  LIMIT 1) AS first,
           (SELECT split_part(line, ' ', 1) FROM windowed ORDER BY seq DESC LIMIT 1) AS last
    `,
    [MONSTER_WINDOW],
  );
  const span = ends?.first && ends?.last ? `${ends.first} → ${ends.last} UTC` : "";

  return { nodes, edges, total, span, scanned, windowed: scanned >= MONSTER_WINDOW };
}

export function where(): { host: string; database: string } {
  try {
    const url = new URL(process.env.AIRE_DATABASE_URL ?? "");
    return { host: url.hostname, database: url.pathname.replace(/^\//, "") || "?" };
  } catch {
    return { host: "?", database: "?" };
  }
}

/* ------------------------------------------------------------------ *
 * The claude memory (backlog #10): folders with Claude inside.       *
 * `project_key` IS the CLI's dash-encoded cwd — one key, one casita. *
 * ------------------------------------------------------------------ */

export type ClaudeFolder = { project_key: string; sessions: number; entries: number; weight_bytes: number; mtime: string };
export type ClaudeSession = { session_id: string; entries: number; mtime: string; first_user: unknown; ai_title: string | null };
export type ClaudeEntry = { entry: unknown; mtime: string };

export async function claudeFolders(): Promise<ClaudeFolder[]> {
  return read<ClaudeFolder>(
    `
    SELECT project_key, count(DISTINCT session_id)::int AS sessions,
           count(*)::int AS entries, sum(length(entry::text))::int AS weight_bytes,
           max(mtime)::text AS mtime
    FROM claude_session_store WHERE subpath = ''
    GROUP BY project_key ORDER BY max(mtime) DESC
    `,
    [],
  );
}

export async function claudeSessions(projectKey: string): Promise<ClaudeSession[]> {
  return read<ClaudeSession>(
    `
    SELECT session_id, count(*)::int AS entries, max(mtime)::text AS mtime,
           (SELECT e2.entry FROM claude_session_store e2
            WHERE e2.project_key = $1 AND e2.session_id = s.session_id
              AND e2.subpath = '' AND e2.entry->>'type' = 'user'
            ORDER BY e2.seq LIMIT 1) AS first_user,
           (SELECT e3.entry->>'aiTitle' FROM claude_session_store e3
            WHERE e3.project_key = $1 AND e3.session_id = s.session_id
              AND e3.subpath = '' AND e3.entry->>'type' = 'ai-title'
            ORDER BY e3.seq DESC LIMIT 1) AS ai_title
    FROM claude_session_store s
    WHERE project_key = $1 AND subpath = ''
    GROUP BY session_id ORDER BY max(mtime) DESC
    `,
    [projectKey],
  );
}

export async function claudeTranscript(projectKey: string, sessionId: string): Promise<ClaudeEntry[]> {
  return read<ClaudeEntry>(
    `
    SELECT entry, mtime::text AS mtime FROM claude_session_store
    WHERE project_key = $1 AND session_id = $2 AND subpath = ''
    ORDER BY seq
    `,
    [projectKey, sessionId],
  );
}

/* ------------------------------------------------------------------ *
 * The gateway's memory (#30/#32): raw API turns, as the door relayed  *
 * them. Two rows per exchange — the request the consumer sent and the *
 * response Anthropic returned — correlated by `exchange` and paired   *
 * here, because a half-turn is not a turn.                            *
 * ------------------------------------------------------------------ */

export type GatewayTurn = {
  exchange: string; ts: string; model: string | null; session_id: string | null;
  project: string | null; holder: string | null; stop_reason: string | null;
  status: number | null; input_tokens: number | null; output_tokens: number | null;
  asked: string | null;
};
export type GatewaySession = {
  session_id: string; project: string | null; holder: string | null;
  model: string | null; turns: number; ts: string; asked: string | null;
};
export type GatewayHalves = {
  request: unknown; response: unknown; ts: string;
  model: string | null; session_id: string | null;
};
export type GatewaySessionTurn = {
  exchange: string; ts: string; model: string | null;
  last_msg: unknown; answer: unknown; stop_reason: string | null;
  input_tokens: number | null; output_tokens: number | null;
};

// `asked` is the TAIL of the last text block, not the head: a Claude Code turn
// opens with pages of system-reminder scaffolding and ends with what the human
// actually said, so the last 160 chars are the readable part.
const ASKED_TAIL = `right(
  CASE WHEN jsonb_typeof(m.content) = 'string' THEN m.content #>> '{}'
       ELSE (SELECT b.v ->> 'text'
             FROM jsonb_array_elements(m.content) WITH ORDINALITY AS b(v, n)
             WHERE b.v ->> 'type' = 'text' ORDER BY b.n DESC LIMIT 1)
  END, 160)`;

// epoch MILLIS as text: that is what freshness() parses, the same shape
// claude_session_store.mtime already has. A timestamptz::text renders an
// empty cell — and the cell often carries the row's link.
const EPOCH_MS = (col: string) => `(extract(epoch FROM ${col}) * 1000)::bigint::text`;

/** Turns that arrived with no session id — loose exchanges, one row each. */
export async function gatewayTurns(limit = 60): Promise<GatewayTurn[]> {
  return read<GatewayTurn>(
    `
    SELECT q.exchange,
           ${EPOCH_MS("coalesce(a.ts, q.ts)")}  AS ts,
           coalesce(a.model, q.model)          AS model,
           q.session_id, q.project, q.holder,
           a.stop_reason, a.status,
           (a.usage->>'input_tokens')::int     AS input_tokens,
           (a.usage->>'output_tokens')::int    AS output_tokens,
           ${ASKED_TAIL}                       AS asked
    FROM aire_gateway_log q
    LEFT JOIN aire_gateway_log a ON a.exchange = q.exchange AND a.kind = 'response'
    CROSS JOIN LATERAL (SELECT jsonb_path_query_first(q.body, '$.messages[last].content') AS content) m
    WHERE q.kind = 'request' AND q.session_id IS NULL
    ORDER BY q.seq DESC LIMIT $1
    `,
    [limit],
  );
}

/** The gateway's conversations: one row per session, newest first — the same
 *  shape /claude gives a casita's sessions, read from the relay's own log. */
export async function gatewaySessions(limit = 60): Promise<GatewaySession[]> {
  return read<GatewaySession>(
    `
    SELECT s.session_id, q.project, q.holder, q.model, s.turns,
           ${EPOCH_MS("q.ts")} AS ts,
           ${ASKED_TAIL}       AS asked
    FROM (SELECT session_id, count(*) AS turns, max(seq) AS last_seq
          FROM aire_gateway_log
          WHERE kind = 'request' AND session_id IS NOT NULL
          GROUP BY session_id) s
    JOIN aire_gateway_log q ON q.seq = s.last_seq
    CROSS JOIN LATERAL (SELECT jsonb_path_query_first(q.body, '$.messages[last].content') AS content) m
    ORDER BY s.last_seq DESC LIMIT $1
    `,
    [limit],
  );
}

/** One session's turns in order. Only the DELTA crosses the wire — the last
 *  message of each request (the rest is history the caller resent) and the
 *  response — because request bodies grow with the conversation and pulling
 *  them whole scales with its square. */
export async function gatewaySession(sessionId: string): Promise<GatewaySessionTurn[]> {
  return read<GatewaySessionTurn>(
    `
    SELECT q.exchange,
           ${EPOCH_MS("coalesce(a.ts, q.ts)")} AS ts,
           coalesce(a.model, q.model)         AS model,
           jsonb_path_query_first(q.body, '$.messages[last]') AS last_msg,
           a.body -> 'content'                AS answer,
           a.stop_reason,
           (a.usage->>'input_tokens')::int    AS input_tokens,
           (a.usage->>'output_tokens')::int   AS output_tokens
    FROM aire_gateway_log q
    LEFT JOIN aire_gateway_log a ON a.exchange = q.exchange AND a.kind = 'response'
    WHERE q.kind = 'request' AND q.session_id = $1
    ORDER BY q.seq
    `,
    [sessionId],
  );
}

export async function gatewayExchange(exchange: string): Promise<GatewayHalves | null> {
  const rows = await read<{ kind: string; body: unknown; ts: string; model: string | null; session_id: string | null }>(
    `SELECT kind, body, ${EPOCH_MS("ts")} AS ts, model, session_id
     FROM aire_gateway_log WHERE exchange = $1 ORDER BY seq`,
    [exchange],
  );
  if (rows.length === 0) return null;
  const request = rows.find((r) => r.kind === "request")?.body ?? null;
  const answer = rows.find((r) => r.kind === "response");
  return {
    request,
    response: answer?.body ?? null,
    ts: rows[0].ts,
    model: answer?.model ?? rows[0].model,
    session_id: rows[0].session_id,
  };
}
