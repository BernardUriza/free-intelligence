import type { SpendDay } from "./db.ts";

/**
 * The spend view's vocabulary: number formatting, the day axis, and the one
 * chart — server-rendered SVG, like the monster's. No charting library, no
 * client JavaScript (decision #5 in CLAUDE.md).
 *
 * Form: stacked columns, one per day, two series (cache read, cache creation).
 * The uncached input is a rounding error beside them (hundreds of tokens
 * against millions) and lives in the table, not the plot — a 1px sliver would
 * only lie about its size. Marks follow the house data-viz spec: ≤24px columns,
 * 4px rounded cap on the top segment, square at the baseline, a 2px surface
 * gap between stacked segments, hairline gridlines, labels in ink tokens.
 */

export const TOKENS_SINCE = "2026-09-15";

export function compact(n: number): string {
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(n >= 1e8 ? 0 : 1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(n >= 1e5 ? 0 : 1)}K`;
  return n.toLocaleString("en-US");
}

export function usd(n: number): string {
  return `$${n.toFixed(n >= 100 ? 0 : 2)}`;
}

/** Today in Bernard's clock, as the ledger cuts its days. */
export function todayMexico(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Mexico_City" }).format(new Date());
}

function shift(day: string, delta: number): string {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + delta)).toISOString().slice(0, 10);
}

/** Every day of the window, in order, with the ledger's row or a silent zero.
 *  A missing day is a day the engine served nothing — the chart shows the
 *  hole instead of closing it (the three-slots-dry outage of 2026-09-12..14 is
 *  exactly such a hole). */
export function fillDays(rows: SpendDay[], days: number, today: string): SpendDay[] {
  const byDay = new Map(rows.map((r) => [r.day, r]));
  const out: SpendDay[] = [];
  for (let i = days; i >= 0; i--) {
    const day = shift(today, -i);
    out.push(byDay.get(day) ?? { day, turns: 0, input: 0, cache_read: 0, cache_creation: 0, usd: 0, usd_metered: 0 });
  }
  return out;
}

/** A clean ceiling for the y axis: 1, 2 or 5 × 10^n above the data max. */
function niceMax(max: number): number {
  if (max <= 0) return 1;
  const p = 10 ** Math.floor(Math.log10(max));
  for (const k of [1, 2, 5, 10]) if (k * p >= max) return k * p;
  return 10 * p;
}

/** Top segment: rounded 4px cap, square where it meets the segment below. */
function capped(x: number, y: number, w: number, h: number): string {
  const r = Math.min(4, h / 2, w / 2);
  return [
    `M${x},${y + h}`, `L${x},${y + r}`, `Q${x},${y} ${x + r},${y}`,
    `L${x + w - r},${y}`, `Q${x + w},${y} ${x + w},${y + r}`, `L${x + w},${y + h}`, "Z",
  ].join(" ");
}

export function TokensByDay({ days }: { days: SpendDay[] }) {
  const W = 880, H = 260, L = 54, R = 12, T = 14, B = 30;
  const plotW = W - L - R, plotH = H - T - B;
  const n = days.length;
  const slot = plotW / n;
  const bw = Math.min(24, Math.max(2, slot * 0.68));
  const totals = days.map((d) => d.cache_read + d.cache_creation);
  const max = niceMax(Math.max(...totals));
  const yOf = (v: number) => T + plotH - (v / max) * plotH;
  const ticks = [0.25, 0.5, 0.75, 1].map((f) => f * max);
  const peak = totals.indexOf(Math.max(...totals));
  const every = n > 60 ? 14 : n > 30 ? 7 : n > 14 ? 3 : 1;
  const gap = 2;

  return (
    <figure className="viz scroll">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Tokens the engine served per day, last ${n - 1} days: cache read and cache creation, stacked.`}
      >
        {ticks.map((v) => (
          <g key={v}>
            <line className="grid" x1={L} x2={W - R} y1={yOf(v)} y2={yOf(v)} />
            <text className="tick" x={L - 8} y={yOf(v) + 3.5} textAnchor="end">{compact(v)}</text>
          </g>
        ))}
        <line className="axis" x1={L} x2={W - R} y1={yOf(0)} y2={yOf(0)} />
        {days.map((d, i) => {
          const x = L + i * slot + (slot - bw) / 2;
          const readH = (d.cache_read / max) * plotH;
          const createH = (d.cache_creation / max) * plotH;
          const yRead = yOf(d.cache_read);
          const both = readH > 0 && createH > 0;
          const yCreate = yRead - createH - (both ? gap : 0);
          const dayN = Number(d.day.slice(8, 10));
          const monthStart = dayN === 1;
          const label = monthStart || i % every === 0 || i === n - 1;
          const title = `${d.day} · ${d.turns} turn${d.turns === 1 ? "" : "s"} · cache read ${compact(d.cache_read)} · cache creation ${compact(d.cache_creation)} · input ${compact(d.input)} · ${usd(d.usd)}`;
          return (
            <g key={d.day}>
              <title>{title}</title>
              <rect className="hit" x={L + i * slot} y={T} width={slot} height={plotH} />
              {readH > 0 && (
                createH > 0
                  ? <rect className="s1" x={x} y={yRead} width={bw} height={readH} />
                  : <path className="s1" d={capped(x, yRead, bw, readH)} />
              )}
              {createH > 0 && <path className="s2" d={capped(x, yCreate, bw, createH)} />}
              {label && (
                <text className="tick" x={x + bw / 2} y={H - 10} textAnchor="middle">
                  {monthStart ? d.day.slice(5, 7) + "/01" : String(dayN)}
                </text>
              )}
              {i === peak && totals[i] > 0 && (
                <text className="peak" x={x + bw / 2} y={Math.max(T + 10, yCreate - 6)} textAnchor="middle">
                  {compact(totals[i])}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      <figcaption className="legend">
        <span><i className="sw s1" /> cache read</span>
        <span><i className="sw s2" /> cache creation</span>
      </figcaption>
    </figure>
  );
}
