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
 * The ORDER is an argument, not a layout: what AIRE is for comes first (the
 * conversations it kept), and the storage those conversations happen to live in
 * comes last, under `raw`. A console that opens on `pg_class` describes the
 * database; this one describes the memory.
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

const VIEWS = [
  { href: "/console", key: "~console", ico: "◈", label: "overview" },
  { href: "/claude", key: "~claude", ico: "▤", label: "conversations" },
  { href: "/gateway", key: "~gateway", ico: "⇄", label: "gateway" },
  { href: "/monster", key: "~monster", ico: "◍", label: "the monster" },
  { href: "/sql", key: "~sql", ico: "⌘", label: "sql console" },
];

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
      <nav className="rail">
        <Link href="/console" className="brand">
          <b>AIRE 🌬️</b>
          <span>the waiter · read only</span>
        </Link>

        <h2>the memory</h2>
        {VIEWS.map((v) => (
          <Link key={v.key} href={v.href} className={v.key === active ? "on" : ""}>
            <span className="ico">{v.ico}</span>
            <span className="lbl">{v.label}</span>
          </Link>
        ))}

        <h2>raw tables</h2>
        <div className="raw">
          {list.length === 0 ? (
            <a>{down ? "— unreachable —" : "— none yet —"}</a>
          ) : (
            list.map((t) => (
              <Link key={t.name} href={`/t/${t.name}`} className={t.name === active ? "on" : ""}>
                <span className="lbl">{t.name}</span>
                <span className="n">{t.rows.toLocaleString("en-US")}</span>
              </Link>
            ))
          )}
        </div>

        <form action={signOut} className="out">
          <button>sign out</button>
        </form>
      </nav>
      <main>{children}</main>
    </div>
  );
}
