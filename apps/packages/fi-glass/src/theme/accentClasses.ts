/**
 * The consumer's accent as Tailwind classes. Written as full literals so a
 * consumer's Tailwind, which scans fi-glass's dist, generates them.
 */

export const ACCENT_TEXT = 'text-[color:var(--fi-accent,#34d399)]';
export const ACCENT_TEXT_HOVER = 'hover:text-[color:var(--fi-accent,#34d399)]';
export const ACCENT_TEXT_LIGHT = 'text-[color:color-mix(in_srgb,var(--fi-accent,#34d399)_70%,white)]';
export const ACCENT_TEXT_LIGHT_HOVER =
  'hover:text-[color:color-mix(in_srgb,var(--fi-accent,#34d399)_70%,white)]';
export const ACCENT_TEXT_MUTED = 'text-[color:color-mix(in_srgb,var(--fi-accent,#34d399)_60%,transparent)]';
export const ACCENT_BG_SOFT = 'bg-[color:color-mix(in_srgb,var(--fi-accent,#34d399)_20%,transparent)]';
export const ACCENT_BG_SOFT_HOVER =
  'hover:bg-[color:color-mix(in_srgb,var(--fi-accent,#34d399)_30%,transparent)]';
