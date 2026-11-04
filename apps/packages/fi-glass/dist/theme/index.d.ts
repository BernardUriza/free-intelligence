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
    /** Shell body background (flat fallback under the layered gradient). */
    body: string;
    /** Page gradient edge color (B3-FIGLASS-13). */
    bgFrom: string;
    /** Page gradient mid color. */
    bgMid: string;
    /** Radial accent glow over the page gradient (consumer re-tints this). */
    bgGlow: string;
    /** Frosted composer/surface fill. */
    surface: string;
    /** Frosted surface border. */
    surfaceBorder: string;
    /** User bubble fill (translucent emerald wash, not solid). */
    bubbleUser: string;
    /** User bubble border. */
    bubbleUserBorder: string;
    /** Assistant bubble fill. */
    bubbleAssistant: string;
    /** Assistant bubble border. */
    bubbleBorder: string;
    /** Brand watermark opacity (image is consumer-supplied via CSS var). */
    watermarkOpacity: string;
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

/**
 * fi-glass · the mobile breakpoint, in ONE place (B3-FIGLASS-TOKEN-LAYER-1).
 *
 * `768px` was written SEVEN times across four different styling layers — the
 * touch-target sheet, the density sheet, the workspace shell's drawer query, the
 * surface layout hook, and three static stylesheets — coordinated only by prose
 * comments ("the 768px breakpoint matches the shell's drawer/mobile query"). A
 * comment is not a constraint: any one of those could drift and the others would
 * keep claiming, in English, that they agreed.
 *
 * WHY THIS IS A TS CONSTANT AND NOT A CSS CUSTOM PROPERTY: a media query cannot
 * read one. `@media (max-width: var(--fi-mobile))` is invalid CSS — custom
 * properties resolve during computed-value time, long after the at-rule is
 * evaluated. So the breakpoint physically cannot live in the token sheet with
 * the rest; the JS-generated sheets interpolate this constant instead, and the
 * three hand-written `.css` files are held to it by `breakpoints.test.ts`,
 * which parses them and fails on any `max-width` that disagrees. Tailwind class
 * strings cannot interpolate it either: they spell `[@media(max-width:768px)]:`
 * (never `max-md:`, which is <768) and the same test holds that literal here.
 */
/** The mobile breakpoint in CSS px. Below/at this width the UI is a phone. */
declare const FI_MOBILE_BREAKPOINT_PX = 768;
/** The canonical mobile media query. Feed it to `useMediaQuery` or a `@media`. */
declare const FI_MOBILE_QUERY = "(max-width: 768px)";
/**
 * The coarse-pointer OR narrow-viewport query — "this is a touch surface".
 * Used by the touch-target minimums, which must also fire on a large tablet
 * that is wide but has no fine pointer.
 */
declare const FI_TOUCH_QUERY = "(pointer: coarse), (max-width: 768px)";

export { FI_MOBILE_BREAKPOINT_PX, FI_MOBILE_QUERY, FI_TOUCH_QUERY, type GlassChatPreset, glassChatPreset };
