/**
 * Try to write through the waiter. Every attempt must fail.
 *
 * This exists because the walls did NOT hold the first time, and the only reason
 * we know that is that the attack was actually RUN instead of reasoned about. On
 * 2026-07-13, against the Python predecessor of `lib/db.ts`, case "disarm the
 * transaction" succeeded: inside a transaction opened READ ONLY, on a connection
 * carrying `default_transaction_read_only=on`, a plain `SET TRANSACTION READ
 * WRITE` was accepted and the INSERT after it went through. A real row of garbage
 * landed in the production log (`aire_log`, seq 2641, `'pwned'`). It is still
 * there — the log is append-only, so the scar stays too.
 *
 * The lesson generalises past this repo: **a read-only transaction MODE is not a
 * read-only CREDENTIAL.** While the role can write, it can always take the
 * privilege back.
 *
 * So the first thing this file does is not an attack at all — it ASKS THE DATABASE
 * whether the role it arrived as is even allowed to write. If it is, the thirteen
 * "blocked" lines below would be a statement about this repo's code rather than
 * about the database's permissions, and the suite refuses to print them. That
 * guard is what stops the credential fix from being silently reverted by a stray
 * env var.
 *
 *     export AIRE_DATABASE_URL=$(grep '^AIRE_DATABASE_URL=' ~/.secrets/aire-postgres-readonly.txt | cut -d= -f2-)
 *     npm run attack
 *
 * Run it after touching `lib/db.ts`, and before believing any sentence that claims
 * this console cannot write.
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

// The wall that cannot be argued with: a credential that LACKS the privilege.
// Everything below this line is defence in depth; THIS is the defence. Ask the
// database — not the config, not a comment — whether the role we arrived as is
// even allowed to write. If it is, someone has handed the waiter the pen's
// credential again, and the thirteen "blocked" lines that follow would be a
// statement about this repo's code rather than about the database's permissions.
const [priv] = (
  await console_(`
    SELECT current_user AS role,
           has_table_privilege(current_user, 'aire_log', 'INSERT') AS can_insert,
           has_table_privilege(current_user, 'aire_log', 'SELECT') AS can_select
  `)
).rows as unknown as { role: string; can_insert: boolean; can_select: boolean }[];

if (!priv.can_select) {
  console.error(`FAILED — connected as '${priv.role}', which cannot even read aire_log.`);
  process.exit(1);
}
if (priv.can_insert) {
  console.error(
    `\nFAILED — connected as '${priv.role}', a role that IS ALLOWED TO INSERT into aire_log.\n` +
      "  The waiter is holding the pen. Point AIRE_DATABASE_URL at aire_reader\n" +
      "  (~/.secrets/aire-postgres-readonly.txt), not at the daemon's credential.\n" +
      "  The four walls in lib/db.ts are defence in depth — they are not the defence.\n",
  );
  process.exit(1);
}
console.log(`connected as '${priv.role}' — reads aire_log, CANNOT insert into it.`);
console.log("the credential itself is the wall; what follows is defence in depth.\n");

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
