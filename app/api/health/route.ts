import { NextResponse } from "next/server";
import { tables } from "../../../lib/db.ts";

export const dynamic = "force-dynamic";

/** The REAL state of the read path, including a downed database, without blowing
 *  up. A health endpoint that answers 500 with a stack trace is useless to the
 *  thing that has to decide whether this revision is alive — and Container Apps
 *  is exactly that thing. */
export async function GET() {
  try {
    const list = await tables();
    return NextResponse.json({
      status: "ok",
      access: "read-only",
      tables: Object.fromEntries(list.map((t) => [t.name, t.rows])),
    });
  } catch (err) {
    return NextResponse.json(
      { status: "degraded", detail: err instanceof Error ? err.name : "Error" },
      { status: 503 },
    );
  }
}
