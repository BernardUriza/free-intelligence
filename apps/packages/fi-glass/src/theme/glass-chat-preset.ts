/**
 * glassChatPreset — the typed mirror of the glass-chat visual preset (B3-V1).
 *
 * The runtime CSS lives next to this file (glass-chat.css) and emits the same
 * values as `--glass-chat-*` custom properties; this object is the typed mirror
 * (same phase-1 contract as `glassTheme` ↔ tokens.css): it gives programmatic
 * access to the values and lets a consumer reference an accent/surface without
 * hardcoding the literal.
 *
 * Glass-material-specific by design: a future `fi-<material>` ships its own chat
 * preset. Domain styling (AURITY's clinical personas) is NOT here — only the
 * reusable glassmorphism chat look.
 */

/** The reusable visual slots of the glass-chat preset. */
export interface GlassChatPreset {
  /** Accent gradient start (emerald). */
  accentFrom: string;
  /** Accent gradient end (cyan). */
  accentTo: string;
  /** Accent text color. */
  accentText: string;
  /** Shell body background. */
  body: string;
  /** Frosted composer/surface fill. */
  surface: string;
  /** Frosted surface border. */
  surfaceBorder: string;
  /** User bubble fill. */
  bubbleUser: string;
  /** Assistant bubble fill. */
  bubbleAssistant: string;
  /** Assistant bubble border. */
  bubbleBorder: string;
  /** Primary text color. */
  text: string;
  /** Muted/secondary text color. */
  textMuted: string;
  /** Elevation shadow (≈ shadow-2xl). */
  shadow: string;
  /** Surface corner radius. */
  radius: string;
}

export const glassChatPreset: GlassChatPreset = {
  accentFrom: '#059669',
  accentTo: '#0891b2',
  accentText: '#6ee7b7',
  body: '#020617',
  surface: 'rgba(30, 41, 59, 0.6)',
  surfaceBorder: 'rgba(71, 85, 105, 0.4)',
  bubbleUser: '#059669',
  bubbleAssistant: 'rgba(30, 41, 59, 0.7)',
  bubbleBorder: 'rgba(71, 85, 105, 0.6)',
  text: '#ffffff',
  textMuted: '#94a3b8',
  shadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
  radius: '14px',
};
