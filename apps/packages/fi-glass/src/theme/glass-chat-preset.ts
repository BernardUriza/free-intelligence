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

import { glassTokens } from './glass-tokens.generated';

/** The reusable visual slots of the glass-chat preset. */
export interface GlassChatPreset {
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

/* Los valores ya no se declaran aquí: vienen del contrato
   (free-intelligence-core/contracts/glass-chat-tokens.json) vía el módulo
   generado — la misma fuente que alimenta el Theme nativo de og118-ios y el
   candado de glass-chat.css. Los nombres del preset se conservan (accentFrom
   es el arranque del gradiente; en el contrato ese valor se llama accentDeep,
   y body/bgFrom siempre fueron el MISMO slate-950 declarado dos veces). */
export const glassChatPreset: GlassChatPreset = {
  accentFrom: glassTokens.accentDeep,
  accentTo: glassTokens.accentTo,
  accentText: glassTokens.accentText,
  body: glassTokens.bgDeep,
  bgFrom: glassTokens.bgDeep,
  bgMid: glassTokens.bgMid,
  bgGlow: glassTokens.glow,
  surface: glassTokens.surface,
  surfaceBorder: glassTokens.surfaceBorder,
  bubbleUser: glassTokens.bubbleUser,
  bubbleUserBorder: glassTokens.bubbleUserBorder,
  bubbleAssistant: glassTokens.bubbleAssistant,
  bubbleBorder: glassTokens.bubbleBorder,
  watermarkOpacity: glassTokens.watermarkOpacity,
  text: glassTokens.text,
  textMuted: glassTokens.textMuted,
  shadow: glassTokens.shadow,
  radius: glassTokens.radius,
};
