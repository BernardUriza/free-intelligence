/**
 * Class-name slots so the consuming app keeps its own CSS — fi-glass ships
 * neutral defaults (empty strings) and never hardcodes app-specific class names
 * (no `iai-*` / `aplay-*` leaking into the framework). insult_ai passes its
 * `iai-card-soft` / `iai-hint` / branded source-row strings to preserve render;
 * og118 passes its own (or nothing for the neutral look).
 */
export interface AgentClassNames {
  /** Card/surface container of a panel. */
  card?: string;
  /** Dimmed small-text hint (counts, queued labels, guard tag). */
  hint?: string;
  /** A single source row (`<a>`) in the Sources panel. */
  sourceRow?: string;
}
