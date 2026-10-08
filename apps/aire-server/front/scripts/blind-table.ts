/**
 * One unreadable table must not blind the whole console.
 *
 * `tables()` reads the catalog — what the DATABASE holds — and then counts each
 * one. The reader's grant covers what the pen owns (`ALTER DEFAULT PRIVILEGES
 * FOR ROLE aire`), which is not the same set: a table created by another role
 * is listed and uncountable. Until 2026-08-22 that single failure threw out of
 * the loop, and because EVERY page renders <Shell>, which needs this list, the
 * console reported the database unreachable over one table it could not count.
 *
 * This proves the isolation on a real database with real grants, the way the
 * attack suite proves the wall: create a table the reader cannot select from,
 * then assert the list still comes back, still carries the readable tables'
 * counts, and reports the unreadable one as null instead of taking the page
 * down with it.
 *
 *     OWNER_DSN=… AIRE_DATABASE_URL=<reader dsn> npm run blind-table
 */

import { Client } from "pg";
import { tables } from "../lib/db.ts";

const BLIND = "aire_unreadable_by_the_reader";

async function main(): Promise<void> {
  const ownerDsn = process.env.OWNER_DSN;
  if (!ownerDsn) throw new Error("OWNER_DSN is required — it creates the unreadable table");

  const owner = new Client({ connectionString: ownerDsn });
  await owner.connect();
  await owner.query(`DROP TABLE IF EXISTS ${BLIND}`);
  await owner.query(`CREATE TABLE ${BLIND} (seq bigserial PRIMARY KEY)`);
  await owner.query(`REVOKE ALL ON ${BLIND} FROM PUBLIC`);

  try {
    const list = await tables();
    const blind = list.find((t) => t.name === BLIND);
    const readable = list.filter((t) => t.name !== BLIND);

    if (!blind) throw new Error(`${BLIND} is missing from the catalog listing`);
    if (blind.rows !== null) throw new Error(`${BLIND} reported ${blind.rows} rows it cannot read`);
    if (readable.length === 0) throw new Error("no other table survived the unreadable one");
    if (readable.some((t) => t.rows === null))
      throw new Error("a table the reader CAN count came back null — the isolation is too wide");

    console.log(`ok — ${readable.length} tables counted, ${BLIND} reported as unreadable`);
  } finally {
    await owner.query(`DROP TABLE IF EXISTS ${BLIND}`);
    await owner.end();
  }
}

main().then(
  () => process.exit(0),
  (err) => {
    console.error(String(err));
    process.exit(1);
  },
);
