export { g as glassTheme } from '../glass-theme-D-leVuKb.js';
import '@free-intelligence/core';

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
interface GlassChatPreset {
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
declare const glassChatPreset: GlassChatPreset;

export { type GlassChatPreset, glassChatPreset };
