import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { signOut } from "../lib/actions.ts";
import { tables, type Table } from "../lib/db.ts";
import { COOKIE, valid } from "../lib/session.ts";

/**
 * The frame every page hangs on: the table list, read from the live catalog on
 * each render. A table the daemon creates tomorrow appears in this sidebar with
 * no code change — the schema is discovered, never hardcoded.
 *
 * It is a Server Component on purpose, so `active` arrives as a prop instead of
 * dragging `usePathname` (and a client bundle) in for one CSS class.
 *
 * It is also the SECOND wall of the door. The proxy is the first, but a proxy
 * bypass is a recurring vulnerability class (CVE-2026-64642 was one), and every
 * page that reads the database renders this frame — so the cookie is re-checked
 * here, in the render path, before any query runs. The advisory's own
 * workaround, kept as permanent depth.
 */
export default async function Shell({
  active = "",
  children,
}: {
  active?: string;
  children: React.ReactNode;
}) {
  const expected = process.env.AIRE_CONSOLE_PASSWORD;
  const token = (await cookies()).get(COOKIE)?.value;
  if (!expected || !(await valid(token, expected))) redirect("/login");
  let list: Table[] = [];
  let down: string | null = null;
  try {
    list = await tables();
  } catch (err) {
    down = err instanceof Error ? err.message : String(err);
  }

  return (
    <div className="shell">
      <nav>
        <Link href="/console" className="brand">
          <b>AIRE front 🌬️</b>
          <span>the waiter — read-only</span>
        </Link>

        <h2>tables</h2>
        {list.length === 0 ? (
          <a>{down ? "— unreachable —" : "— none yet —"}</a>
        ) : (
          list.map((t) => (
            <Link key={t.name} href={`/t/${t.name}`} className={t.name === active ? "on" : ""}>
              {t.name}
              <span className="n">{t.rows.toLocaleString("en-US")}</span>
            </Link>
          ))
        )}

        <h2>views</h2>
        <Link href="/claude" className={active === "~claude" ? "on" : ""}>
          claude
        </Link>
        <Link href="/gateway" className={active === "~gateway" ? "on" : ""}>
          gateway
        </Link>
        <Link href="/monster" className={active === "~monster" ? "on" : ""}>
          the monster
        </Link>
        <Link href="/sql" className={active === "~sql" ? "on" : ""}>
          sql console
        </Link>

        <form action={signOut} className="out">
          <button>sign out</button>
        </form>
      </nav>
      <main>{children}</main>
    </div>
  );
}
