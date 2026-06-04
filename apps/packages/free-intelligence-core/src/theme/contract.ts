/**
 * ThemeTokens — the material-agnostic slot contract for a frosted-surface theme.
 *
 * Every `fi-<material>` skin (fi-glass today; future fi-slate, fi-paper, …) fills
 * these same slots with its own values. Consumers — fi-glass's shell/agentic
 * components and the apps themselves — depend only on this shape, never on a
 * concrete material. That is precisely what makes "material = token swap" hold
 * without any material having to depend on another.
 *
 * This is pure data: no React, no styling, no logic. It lives in core so a future
 * material never has to reach into fi-glass just to learn the slot shape.
 */
export interface ThemeTokens {
  /** Backdrop blur radius for frosted surfaces, e.g. `"12px"`. */
  blur: string;
  /** Reduced blur radius for small viewports (≤768px), e.g. `"8px"`. */
  blurCompact: string;
  /** Surface fill opacity, `0..1`. */
  opacity: number;
  /** Backdrop saturation boost, e.g. `"180%"`. */
  saturation: string;
  /** Light surface base fill as an `"r, g, b"` triple, e.g. `"255, 255, 255"`. */
  surfaceLight: string;
  /** Light surface border (full CSS color), e.g. `"rgba(255, 255, 255, 0.18)"`. */
  borderLight: string;
  /** Dark surface fill (full CSS color), e.g. `"rgba(15, 23, 42, 0.7)"`. */
  surfaceDark: string;
  /** Dark surface border (full CSS color), e.g. `"rgba(148, 163, 184, 0.2)"`. */
  borderDark: string;
}
