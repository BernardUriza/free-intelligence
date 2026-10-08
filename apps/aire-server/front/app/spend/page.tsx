import Link from "next/link";
import Shell from "../../components/Shell.tsx";
import { spendDaily } from "../../lib/db.ts";
import { compact, fillDays, todayMexico, TokensByDay, TOKENS_SINCE, usd } from "../../lib/spend.tsx";

export const dynamic = "force-dynamic";

export const metadata = { title: "AIRE — spend" };

const WINDOWS = [30, 60, 90, 180];

/** What the engine served, day by day: turns, tokens and the dollars it banked
 *  (`aire_spend`). Nominal dollars are what an OAuth turn would have cost — the
 *  Max subscription already paid them; metered dollars are the ones a card paid. */
export default async function SpendPage({
  searchParams,
}: {
  searchParams: Promise<{ days?: string }>;
}) {
  const { days: raw } = await searchParams;
  const days = WINDOWS.includes(Number(raw)) ? Number(raw) : 60;
  const today = todayMexico();
  const rows = await spendDaily(days);
  const series = fillDays(rows, days, today);
  const sum = (k: "turns" | "input" | "cache_read" | "cache_creation" | "usd" | "usd_metered") =>
    rows.reduce((n, r) => n + r[k], 0);
  const tokens = sum("input") + sum("cache_read") + sum("cache_creation");
  const untracked = rows.filter((r) => r.day < TOKENS_SINCE && r.turns > 0).length;

  return (
    <Shell active="~spend">
      <h1>spend</h1>
      <p className="sub">
        What the engine door served, day by day, read from <code>aire_spend</code>. Days are
        cut in Mexico City. Dollars are nominal unless marked metered.
      </p>

      <div className="bar windows">
        {WINDOWS.map((w) => (
          <Link key={w} href={`/spend?days=${w}`} className={w === days ? "on" : ""}>
            {w} days
          </Link>
        ))}
      </div>

      <p className="hero">
        {compact(tokens)}
        <span className="hero-k">tokens served in the last {days} days</span>
      </p>

      <div className="tiles">
        <span className="tile">
          <span className="k">turns</span>
          <span className="v">{sum("turns").toLocaleString("en-US")}</span>
          <span className="u">engine door, every session</span>
        </span>
        <span className="tile">
          <span className="k">cache read</span>
          <span className="v">{compact(sum("cache_read"))}</span>
          <span className="u">prompt served warm</span>
        </span>
        <span className="tile">
          <span className="k">cache creation</span>
          <span className="v">{compact(sum("cache_creation"))}</span>
          <span className="u">prompt written to cache</span>
        </span>
        <span className="tile">
          <span className="k">input, uncached</span>
          <span className="v">{compact(sum("input"))}</span>
          <span className="u">what the callers typed</span>
        </span>
        <span className="tile">
          <span className="k">nominal</span>
          <span className="v">{usd(sum("usd"))}</span>
          <span className="u">
            {sum("usd_metered") > 0 ? `${usd(sum("usd_metered"))} of it metered` : "none of it metered"}
          </span>
        </span>
      </div>

      <div className="panel">
        <TokensByDay days={series} />
        {untracked > 0 && (
          <p className="note">
            The token columns exist since {TOKENS_SINCE}: {untracked} earlier day
            {untracked === 1 ? "" : "s"} in this window carr{untracked === 1 ? "ies" : "y"} turns
            and dollars only, and draw{untracked === 1 ? "s" : ""} no column.
          </p>
        )}
      </div>

      <div className="panel">
        <div className="scroll">
          <table>
            <thead>
              <tr>
                <th>day</th>
                <th className="num">turns</th>
                <th className="num">input</th>
                <th className="num">cache read</th>
                <th className="num">cache creation</th>
                <th className="num">nominal</th>
                <th className="num">metered</th>
              </tr>
            </thead>
            <tbody>
              {[...rows].reverse().map((r) => (
                <tr key={r.day}>
                  <td className="name">{r.day}</td>
                  <td className="num">{r.turns.toLocaleString("en-US")}</td>
                  <td className="num">{r.day < TOKENS_SINCE ? "—" : r.input.toLocaleString("en-US")}</td>
                  <td className="num">{r.day < TOKENS_SINCE ? "—" : r.cache_read.toLocaleString("en-US")}</td>
                  <td className="num">{r.day < TOKENS_SINCE ? "—" : r.cache_creation.toLocaleString("en-US")}</td>
                  <td className="num">{usd(r.usd)}</td>
                  <td className="num">{r.usd_metered > 0 ? usd(r.usd_metered) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 && <p className="empty">nothing banked in the last {days} days.</p>}
        </div>
      </div>
    </Shell>
  );
}
