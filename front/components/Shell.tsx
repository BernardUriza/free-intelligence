import Link from "next/link";
import { signOut } from "../lib/actions.ts";
import { tables, type Table } from "../lib/db.ts";

/**
 * The frame every page hangs on: the table list, read from the live catalog on
 * each render. A table the daemon creates tomorrow appears in this sidebar with
 * no code change — the schema is discovered, never hardcoded.
 *
 * It is a Server Component on purpose, so `active` arrives as a prop instead of
 * dragging `usePathname` (and a client bundle) in for one CSS class.
 */
export default async function Shell({
  active = "",
  children,
}: {
  active?: string;
  children: React.ReactNode;
}) {
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
        <div className="brand">
          <b>AIRE front 🌬️</b>
          <span>the waiter — read-only</span>
        </div>

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
