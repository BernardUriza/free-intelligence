import type { ThemeTokens } from '@free-intelligence/core';

/**
 * glassTheme — the concrete values that fill core's ThemeTokens slots for the
 * `fi-glass` material.
 *
 * The runtime CSS lives next to this file (tokens.css / glass.css) and emits the
 * same values as `--glass-*` custom properties. This object is the typed mirror:
 * it gives programmatic access to the values and lets future materials
 * (fi-slate, fi-paper, …) be diffed against the very same slot shape.
 *
 * NOTE: values are intentionally duplicated between this object and tokens.css
 * during phase 1 (CSS is the runtime source of truth; this is documentation +
 * typing). A later phase may generate the CSS from this object to remove the
 * duplication — deliberately out of scope here.
 */
export const glassTheme: ThemeTokens = {
  blur: '12px',
  blurCompact: '8px',
  opacity: 0.8,
  saturation: '180%',
  surfaceLight: '255, 255, 255',
  borderLight: 'rgba(255, 255, 255, 0.18)',
  surfaceDark: 'rgba(15, 23, 42, 0.7)',
  borderDark: 'rgba(148, 163, 184, 0.2)',
};
