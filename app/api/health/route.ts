import { NextResponse } from "next/server";
import { pool } from "../../../lib/db.ts";

export const dynamic = "force-dynamic";

/**
 * The REAL state of the read path — the process is up AND Postgres answers —
 * without blowing up when the database is down. A health endpoint that returns a
 * 500 with a stack trace is useless to the thing that has to decide whether this
 * revision is alive, and Container Apps is exactly that thing.
 *
 * This is the ONE route the middleware lets through unauthenticated, because a
 * liveness probe cannot carry a credential. So it is also the one route that must
 * give nothing away: it used to answer with the table names and their row counts,
 * which is the database's schema, published to anyone who asked. It reports that
 * it can read. It does not report WHAT.
 */
export async function GET() {
  try {
    const client = await pool().connect();
    try {
      await client.query("BEGIN READ ONLY");
      await client.query({ text: "SELECT 1", values: [] });
      await client.query("COMMIT");
    } finally {
      client.release();
    }
    return NextResponse.json({ status: "ok", access: "read-only" });
  } catch (err) {
    return NextResponse.json(
      { status: "degraded", detail: err instanceof Error ? err.name : "Error" },
      { status: 503 },
    );
  }
}
