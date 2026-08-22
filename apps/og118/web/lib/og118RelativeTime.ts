/**
 * "Actualizado hace 6 días" — og118's words, not fi-glass's.
 *
 * The framework's cards take an already-formatted node precisely so the language
 * lives here. Built on `Intl.RelativeTimeFormat`, which every target browser has,
 * instead of a hand-rolled pluralization table that gets "hace 1 días" wrong.
 *
 * `now` is injectable so a test can assert a formatting rule without waiting for
 * the clock, and so nothing here reads the wall clock at render time.
 */

const DIVISIONS: [seconds: number, unit: Intl.RelativeTimeFormatUnit][] = [
  [60, 'second'],
  [3600, 'minute'],
  [86400, 'hour'],
  [604800, 'day'],
  [2629800, 'week'],
  [31557600, 'month'],
  [Infinity, 'year'],
];

const UNIT_SECONDS: Record<string, number> = {
  second: 1,
  minute: 60,
  hour: 3600,
  day: 86400,
  week: 604800,
  month: 2629800,
  year: 31557600,
};

/**
 * A relative phrase in Spanish, or `null` when the timestamp is missing or
 * unparseable — the caller then renders nothing rather than "Invalid Date",
 * which is what a naive `new Date(x)` puts on screen.
 */
export function relativeTime(iso: string | undefined, now: number = Date.now()): string | null {
  if (!iso) return null;
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return null;
  const elapsed = (then - now) / 1000;
  const magnitude = Math.abs(elapsed);
  if (magnitude < 45) return 'hace un momento';
  const fmt = new Intl.RelativeTimeFormat('es', { numeric: 'auto' });
  for (const [limit, unit] of DIVISIONS) {
    if (magnitude < limit) {
      return fmt.format(Math.round(elapsed / UNIT_SECONDS[unit]), unit);
    }
  }
  return null;
}
