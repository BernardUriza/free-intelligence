// DO NOT EDIT — generado desde contracts/glass-chat-tokens.json
//
// El contrato es LA FUENTE, escrita a mano. El CSS de fi-glass, el mirror
// tipado glassChatPreset y este Theme derivan de él; ninguna superficie manda
// sobre las otras. Un token transcrito a ojo diverge — así se despintó el
// espejo nativo del preset más de una vez.
//
// Regla de conversión: 1rem = 16px en la web y 1px CSS = 1pt en iOS, así que
// pt = round(rem × 16). Los redondeos (0.55rem→9pt, 0.68rem→11pt) caen de la
// regla, no de una tabla aparte.
//
//   pnpm --filter @free-intelligence/core gen:swift-theme
//   pnpm --filter @free-intelligence/core check:swift-theme

import SwiftUI

extension Theme {
    /// slate-950. --glass-chat-body y --glass-chat-bg-from del preset. OJO: og118 web re-tinta --glass-chat-bg-from a #0a0e16 (--og-bg-deep en globals.css); el iPhone hoy pinta el default del preset, no el re-tint — divergencia heredada, documentada, no resuelta aquí.
    /// OVERRIDE de og118: og118 arranca su fondo más arriba que slate-950: --glass-chat-bg-from apunta a --og-bg-deep.
    static let bgDeep = Color(hex: 0x0A0E16)
    /// slate-900. --glass-chat-bg-mid, el centro del barrido diagonal del fondo.
    static let bgMid = Color(hex: 0x0F172A)
    /// emerald-400. --og-accent en globals.css de og118 — el acento del CONSUMER, no del preset (el preset arranca su gradiente en accentDeep).
    static let accent = Color(hex: 0x34D399)
    /// emerald-600. --glass-chat-accent-from del preset; tambien el extremo final del gradiente del botón de enviar de og118.
    static let accentDeep = Color(hex: 0x059669)
    /// cyan-600. --glass-chat-accent-to: cierra el gradiente header/CTA del preset. Hoy sólo la web lo usa.
    static let accentTo = Color(hex: 0x0891B2)
    /// emerald-300. --glass-chat-accent-text. Hoy sólo la web lo usa.
    static let accentText = Color(hex: 0x6EE7B7)
    /// --og-accent-muted en globals.css. OJO: globals.css tiene un fallback var(--og-accent-muted, #94a3b8) que no coincide con la definición de :root — bug preexistente de la web.
    static let accentMuted = Color(hex: 0xA3A3A3)
    /// red-400. --og-danger y el fallback de --fi-sidebar-item-danger en sidebarItemStyle.ts.
    static let danger = Color(hex: 0xF87171)
    /// --glass-chat-text, el texto primario sobre el vidrio.
    static let text = Color(hex: 0xFFFFFF)
    /// slate-200. El color de body en og118 y content.user en messages/styles.ts. La web pinta al asistente un paso más claro (slate-100, text-slate-100); el iPhone usa este mismo para ambos lados — matiz heredado.
    static let textBody = Color(hex: 0xE2E8F0)
    /// slate-400. --glass-chat-text-muted: placeholders y subtítulos.
    static let textMuted = Color(hex: 0x94A3B8)
    /// slate-500. Timestamps (MessageAuthorHeader), placeholders terciarios.
    static let textFaint = Color(hex: 0x64748B)
    /// slate-800/60. --glass-chat-surface: el relleno esmerilado del composer.
    static let surface = Color(hex: 0x1E293B).opacity(0.6)
    /// slate-600/40. --glass-chat-surface-border.
    static let surfaceBorder = Color(hex: 0x475569).opacity(0.4)
    /// emerald-600/32. --glass-chat-bubble-user: lavado esmeralda translúcido, no sólido — el sólido leía como verde WhatsApp.
    static let bubbleUser = Color(hex: 0x059669).opacity(0.32)
    /// emerald-400/25. --glass-chat-bubble-user-border.
    static let bubbleUserBorder = Color(hex: 0x34D399).opacity(0.25)
    /// slate-800/55. --glass-chat-bubble-assistant.
    static let bubbleAssistant = Color(hex: 0x1E293B).opacity(0.55)
    /// slate-600/35. --glass-chat-bubble-border.
    static let bubbleBorder = Color(hex: 0x475569).opacity(0.35)
    /// --glass-chat-bg-glow del preset: el resplandor radial apenas-visible sobre el fondo. OJO: og118 web lo re-tinta a rgba(52, 211, 153, 0.06) — 'og emerald, not preset cyan'; el iPhone hoy pinta el cyan del preset — divergencia heredada, documentada, no resuelta aquí.
    /// OVERRIDE de og118: El resplandor radial de og118 es esmeralda, no el cyan del preset. globals.css lo dice literal: "og emerald, not preset cyan".
    static let glow = Color(hex: 0x34D399).opacity(0.06)
    /// violet-600/80. avatar.user en messages/styles.ts: el chip de autor del usuario.
    static let authorUser = Color(hex: 0x7C3AED).opacity(0.8)
    /// --fi-author-agent-fg en MessageAuthorHeader.tsx: texto oscuro sobre el chip ámbar del agente.
    static let authorAgentText = Color(hex: 0x0A0F1E)
    /// slate-300. El nombre del hablante en MessageAuthorHeader.tsx (meta.name).
    static let authorName = Color(hex: 0xCBD5E1)
    /// amber-400/80. typing.dot en messages/styles.ts.
    static let typingDot = Color(hex: 0xFBBF24).opacity(0.8)
    /// amber-300/90. markdownStyles.code — el ámbar del código inline, distinto a propósito del esmeralda de los links.
    static let codeInline = Color(hex: 0xFCD34D).opacity(0.9)
    /// slate-900/80. markdownStyles.pre.
    static let codeBlockBg = Color(hex: 0x0F172A).opacity(0.8)
    /// slate-700/30. Borde de markdownStyles.pre.
    static let codeBlockBorder = Color(hex: 0x334155).opacity(0.3)
    /// white/3. markdownStyles.blockquote.
    static let quoteBg = Color(hex: 0xFFFFFF).opacity(0.03)
    /// amber-500/60. El filete izquierdo del blockquote.
    static let quoteAccent = Color(hex: 0xF59E0B).opacity(0.6)
    /// emerald-500/30. Borde del selector de elemento (Og118ElementSelector).
    static let chipBorder = Color(hex: 0x10B981).opacity(0.3)
    /// white/5. Relleno del selector de elemento.
    static let chipFill = Color(hex: 0xFFFFFF).opacity(0.05)
    /// El tinte .is-selected de la fila del sidebar (sidebarItemStyle.ts).
    static let itemSelectedBg = Color(hex: 0x34D399).opacity(0.08)
    /// El borde .is-selected de la fila del sidebar.
    static let itemSelectedBorder = Color(hex: 0x34D399).opacity(0.3)
    /// white/4. Fallback de --fi-sidebar-item-hover-bg.
    static let itemHover = Color(hex: 0xFFFFFF).opacity(0.04)
    /// slate-600. Fallback de --fi-sidebar-item-meta-color: la hora de la fila.
    static let itemMeta = Color(hex: 0x475569)
    /// slate-500. Fallback de --fi-sidebar-item-action-color: los botones de la fila.
    static let itemAction = Color(hex: 0x64748B)
    /// white/6. Los bordes del rail (.og-sidebar, .og-sidebar-foot, .og-sidebar-archived).
    static let sidebarDivider = Color(hex: 0xFFFFFF).opacity(0.06)
    /// white/4. Fondo de .og-sidebar-search.
    static let searchFill = Color(hex: 0xFFFFFF).opacity(0.04)
    /// white/10. Borde de .og-sidebar-search.
    static let searchBorder = Color(hex: 0xFFFFFF).opacity(0.1)
    /// emerald-500/30. El badge del elemento seleccionado (bg-emerald-500/30).
    static let badgeSelected = Color(hex: 0x10B981).opacity(0.3)
    /// emerald-100. Texto del badge seleccionado (text-emerald-100).
    static let badgeSelectedText = Color(hex: 0xD1FAE5)
    /// emerald-500/10. Relleno del chip de engine (bg-emerald-500/10).
    static let engineChipFill = Color(hex: 0x10B981).opacity(0.1)
    /// slate-600. Fondo del swipe de archivar — affordance NATIVA del iPhone, sin gemelo web; el tono viene de la misma escala slate del rail.
    static let archiveSwipe = Color(hex: 0x475569)
    /// Texto oscuro sobre el gradiente esmeralda del botón de enviar (.og-send-btn color).
    static let sendText = Color(hex: 0x052E1A)
    /// El outline del enviar deshabilitado (.og-send-btn:disabled): mantiene la FORMA del control en el estado que más se ve.
    static let sendDisabledBorder = Color(hex: 0x94A3B8).opacity(0.28)
    /// red-600/90. .og-stop-btn: el rojo dice 'esto lo detiene'.
    static let stopFill = Color(hex: 0xDC2626).opacity(0.9)
    /// red-400/60. Borde de .og-stop-btn.
    static let stopBorder = Color(hex: 0xF87171).opacity(0.6)
    /// red-100. Texto de .og-stop-btn.
    static let stopText = Color(hex: 0xFEE2E2)

    /// --glass-chat-radius (rounded-2xl): la esquina del composer y las superficies grandes. (16px)
    static let radius: CGFloat = 16
    /// La esquina de la fila del sidebar (sidebarItemStyle.ts). (10px)
    static let itemRadius: CGFloat = 10
    /// Fallback de --fi-item-gap (densidad comfortable). (0.4rem -> 6pt)
    static let itemGap: CGFloat = 6
    /// Padding vertical de la fila (primera mitad de --fi-item-padding comfortable). (0.55rem -> 9pt)
    static let itemPadV: CGFloat = 9
    /// Padding horizontal de la fila (segunda mitad de --fi-item-padding comfortable). (0.6rem -> 10pt)
    static let itemPadH: CGFloat = 10
    /// Tipografía del título de la fila. (0.85rem -> 14pt)
    static let itemTitleSize: CGFloat = 14
    /// Tipografía del subtítulo/preview de la fila. (0.75rem -> 12pt)
    static let itemSubtitleSize: CGFloat = 12
    /// Tipografía de la hora/meta de la fila. (0.68rem -> 11pt)
    static let itemMetaSize: CGFloat = 11
}
