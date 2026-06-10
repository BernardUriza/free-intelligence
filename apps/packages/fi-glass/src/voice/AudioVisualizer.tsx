'use client';

/**
 * fi-glass · AudioVisualizer — reusable audio-level graphic (bars / pulse).
 *
 * The visual half of the voice UX that AURITY had baked into its clinical
 * capture screen: animated bars and pulsing rings that react to audio level.
 * Extracted here as a pure, presentational primitive so any surface — a TTS
 * player, a recording composer, a future shell — can render levels without
 * pulling in Web Audio, a microphone, or the network.
 *
 * Deliberately data-driven: it renders whatever normalized `levels` (0..1) it
 * is handed. Real consumers feed it analyser output (e.g. `useAudioAnalysis`
 * scaled to 0..1); tests feed it a fixed array. No effects, no timers, no
 * randomness — same props in, same DOM out — so it is unit-testable with static
 * rendering and never depends on a live mic.
 *
 * Accessibility: it is a non-interactive graphic, exposed as role="img" with a
 * label so assistive tech announces it as a single "audio level" image rather
 * than a pile of empty divs.
 */

export type AudioVisualizerVariant = 'bars' | 'pulse';

export interface AudioVisualizerProps {
  /**
   * Normalized amplitude samples in [0, 1]. Out-of-range values are clamped.
   * For `bars`, each sample is one bar; for `pulse`, the peak drives the ring.
   */
  levels: number[];
  /** Visual style. Default 'bars'. */
  variant?: AudioVisualizerVariant;
  /**
   * Whether the source is actively producing audio. When false the graphic
   * renders at rest (flat bars / collapsed pulse) regardless of `levels`, so a
   * paused player or an idle mic reads as silent.
   */
  active?: boolean;
  /**
   * For `bars`: force a fixed bar count, resampling `levels` to fit. Defaults to
   * `levels.length`. Lets a surface keep a stable bar count across frames.
   */
  barCount?: number;
  /** Accessible label. Default 'Visualizador de nivel de audio'. */
  label?: string;
  /** Wrapper class. */
  className?: string;
  /** Per-bar class (bars variant). */
  barClassName?: string;
  /** Fill color applied inline (bars background / pulse border). */
  color?: string;
}

const MIN_BAR_PCT = 4; // keep a sliver visible at silence

/** Clamp to [0,1] and drop non-finite values to 0. Pure + exported for tests. */
export function normalizeLevels(levels: number[]): number[] {
  return levels.map((v) =>
    !Number.isFinite(v) ? 0 : v < 0 ? 0 : v > 1 ? 1 : v
  );
}

/**
 * Resample an array to exactly `count` points by nearest-index sampling. Pure +
 * exported so the resampling rule is unit-tested. Returns zeros for count<=0.
 */
export function resampleLevels(levels: number[], count: number): number[] {
  if (count <= 0) return [];
  if (levels.length === 0) return new Array(count).fill(0);
  if (levels.length === count) return levels.slice();
  const out: number[] = [];
  for (let i = 0; i < count; i++) {
    const idx = Math.min(
      levels.length - 1,
      Math.floor((i / count) * levels.length)
    );
    out.push(levels[idx]);
  }
  return out;
}

export function AudioVisualizer({
  levels,
  variant = 'bars',
  active = true,
  barCount,
  label = 'Visualizador de nivel de audio',
  className,
  barClassName,
  color,
}: AudioVisualizerProps) {
  const normalized = normalizeLevels(levels);

  if (variant === 'pulse') {
    const peak = active && normalized.length ? Math.max(...normalized) : 0;
    const scale = 1 + peak; // 1.0 at rest -> 2.0 at full
    return (
      <div
        role="img"
        aria-label={label}
        className={className}
        data-fi-audio-visualizer="pulse"
        data-active={active ? '' : undefined}
      >
        <span
          data-fi-pulse-core=""
          style={{
            display: 'inline-block',
            transform: `scale(${scale})`,
            borderColor: color,
          }}
        />
      </div>
    );
  }

  // bars
  const count = barCount && barCount > 0 ? barCount : normalized.length;
  const bars = resampleLevels(normalized, count);
  return (
    <div
      role="img"
      aria-label={label}
      className={className}
      data-fi-audio-visualizer="bars"
      data-active={active ? '' : undefined}
      style={{ display: 'inline-flex', alignItems: 'flex-end' }}
    >
      {bars.map((level, i) => {
        const pct = active ? Math.max(MIN_BAR_PCT, level * 100) : MIN_BAR_PCT;
        return (
          <span
            key={i}
            data-fi-audio-bar=""
            className={barClassName}
            style={{ height: `${pct}%`, backgroundColor: color }}
          />
        );
      })}
    </div>
  );
}
