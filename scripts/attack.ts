/**
 * Try to write through the waiter. Every attempt must fail.
 *
 * This exists because the walls did NOT hold the first time, and the only reason
 * we know that is that the attack was actually RUN instead of reasoned about. On
 * 2026-07-13, against the Python predecessor of `lib/db.ts`, case "disarm the
 * transaction" succeeded: inside a transaction opened READ ONLY, on a connection
 * carrying `default_transaction_read_only=on`, a plain `SET TRANSACTION READ
 * WRITE` was accepted and the INSERT after it went through. A real row of garbage
 * landed in the production log (`aire_log`, seq 2641, `'pwned'`).
 *
 * The lesson generalises past this repo: a read-only *transaction mode* is not a
 * read-only *credential*. While the role can write, it can always take the
 * privilege back.
 *
 * Run after touching `lib/db.ts`, and before believing any sentence that claims
 * this console cannot write:
 *
 *     export AIRE_DATABASE_URL=...
 *     npm run attack
 *
 * The day the credential is `aire_reader` (GRANT SELECT and nothing more), every
 * case here must STILL pass with the walls in `lib/db.ts` deleted. That is the
 * test that the real fix is real.
 */

import { console_, pool } from "../lib/db.ts";

const MARK = "attack-probe-do-not-write";

const ATTACKS: [string, string][] = [
  ["plain DELETE", `DELETE FROM aire_log WHERE line = '${MARK}'`],
  ["plain INSERT", `INSERT INTO aire_log (line) VALUES ('${MARK}')`],
  ["plain UPDATE", `UPDATE aire_log SET line = '${MARK}' WHERE seq = 1`],
  ["DROP TABLE", "DROP TABLE aire_log"],
  ["CREATE TABLE", "CREATE TABLE attack_probe (a int)"],
  ["TRUNCATE", "TRUNCATE aire_log"],
  ["disarm the default", "SET default_transaction_read_only = off"],
  ["disarm the transaction", "SET TRANSACTION READ WRITE"],
  // The one that node-postgres makes reachable and asyncpg did not: the simple
  // query protocol runs both halves in one round trip, inside ONE transaction.
  ["disarm, then write", `SET TRANSACTION READ WRITE; INSERT INTO aire_log (line) VALUES ('${MARK}')`],
  ["read, then write", `SELECT 1; INSERT INTO aire_log (line) VALUES ('${MARK}')`],
  ["data-modifying CTE", `WITH x AS (INSERT INTO aire_log (line) VALUES ('${MARK}') RETURNING seq) SELECT * FROM x`],
  ["write inside a DO block", `DO $$ BEGIN INSERT INTO aire_log (line) VALUES ('${MARK}'); END $$`],
  ["COPY from a file", "COPY aire_log FROM '/etc/passwd'"],
];

// Prove there is a database on the other end BEFORE trusting a single "blocked".
// Wall 4 (the regex) refuses most of these without ever opening a connection, so
// a run with no reachable Postgres reports nine cheerful `blocked NotARead` lines
// and proves NOTHING — the walls that actually matter (1, 2 and 3 live in the
// engine) were never exercised. That is the exact fake-green this file exists to
// kill, and it shipped once: CI printed a wall of "blocked" against an empty
// AIRE_DATABASE_URL.
const [{ one }] = (await console_("SELECT 1 AS one")).rows as unknown as { one: number }[];
if (one !== 1) {
  console.error("The database did not answer SELECT 1. Refusing to report on walls that were never tested.");
  process.exit(1);
}
console.log("database reachable — the engine-level walls are in play\n");

const breached: string[] = [];

for (const [name, sql] of ATTACKS) {
  try {
    await console_(sql);
    breached.push(name);
    console.log(`  BREACH   ${name.padEnd(24)} the statement was ACCEPTED`);
  } catch (err) {
    const kind = err instanceof Error ? err.name : "?";
    console.log(`  blocked  ${name.padEnd(24)} ${kind}`);
  }
}

const { rows } = await console_(
  `SELECT count(*)::int AS landed FROM aire_log WHERE line = '${MARK}'`,
);
const landed = Number(rows[0]?.landed ?? -1);
await pool().end();

console.log();
if (breached.length > 0 || landed > 0) {
  console.log(`FAILED — ${breached.length} statement(s) accepted, ${landed} garbage row(s) in aire_log.`);
  if (landed > 0) {
    console.log(`  Clean up from aire-server (it holds the pen): DELETE FROM aire_log WHERE line = '${MARK}';`);
  }
  process.exit(1);
}
console.log(`PASSED — ${ATTACKS.length} write attempts, all refused, aire_log untouched.`);
process.exit(0);
