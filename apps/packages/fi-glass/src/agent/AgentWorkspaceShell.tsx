'use client';

/**
 * AgentWorkspaceShell — the viewport-locked agent-workspace PAGE primitive
 * (FG-4, canary-driven upstream loop, captured by activist-os's FiGlassPrimary).
 *
 * FG-1/FG-2 gave AgentConversationSurface a `layout="contained"` mode so it can
 * live inside a fixed-height cell. But every consumer still hand-rolled the page
 * that wraps it: header + main grid + conversation column + artifact rail +
 * footer, viewport-locked with no page overflow. This primitive composes that
 * page from SLOTS — the next rung toward declarative AgentAppScreen templates.
 *
 * It is pure composition: the conversation is a slot (the app passes its own
 * AgentConversationSurface), not constructed here. Material-agnostic and
 * app-neutral — markers/classes only, no real aurora visual CSS yet.
 *
 * B3-FIGLASS-MOBILE-1: an optional left `sidebar` slot (e.g. a chat list) with an
 * opt-in mobile drawer. Without `sidebar` the output is byte-identical to the
 * original page primitive (activist-os unaffected). With `sidebar` + `responsive`,
 * the sidebar is a static left column on desktop and an off-canvas drawer below
 * `mobileQuery` — hamburger toggle, tap-overlay/Escape/selection close, body
 * scroll lock, inert+aria-hidden when closed. The consumer closes the drawer on
 * selection via the render-prop api (`{ close }`), so fi-glass never reaches into
 * the consumer's DOM. Inline styles + one idempotent <style> tag → zero
 * CSS-coupling, no consumer import.
 *
 * B3-FIGLASS-SEMANTIC-SHELL-1: the slot wrappers are DOM landmarks, not bare divs —
 * `<header>`/`<main>`/`<aside>` (rail)/`<footer>` for the page column and a labelled
 * `<nav>` for the sidebar. The `data-fi-slot` attributes and inline styles are
 * preserved, so the change is visual-equivalent and consumers need no new CSS.
 */

import {
  useCallback,
  useEffect,
  useState,
  type CSSProperties,
  type ReactNode,
} from 'react';
import { Menu } from 'lucide-react';
import { useMediaQuery } from '../shell/useMediaQuery';
import { useDensityStyle } from './densityStyle';

export type AgentWorkspaceShellVisual = 'aurora' | 'midnight' | 'clinical';
export type AgentWorkspaceShellDensity = 'compact' | 'comfortable' | 'spacious';

/** Imperative drawer controls handed to the sidebar slot in `responsive` mode. */
export interface AgentWorkspaceShellApi {
  /** Whether the mobile drawer is open (always false on desktop / non-responsive). */
  isOpen: boolean;
  /** Whether the shell is in the mobile/drawer breakpoint. */
  isMobile: boolean;
  open: () => void;
  close: () => void;
  toggle: () => void;
}

type SidebarSlot = ReactNode | ((api: AgentWorkspaceShellApi) => ReactNode);

export interface AgentWorkspaceShellProps {
  visual?: AgentWorkspaceShellVisual;
  density?: AgentWorkspaceShellDensity;
  header?: ReactNode;
  conversation: ReactNode;
  rail?: ReactNode;
  footer?: ReactNode;
  /**
   * Optional left chrome (e.g. a conversation list). A render function receives
   * the drawer api so the consumer can `close()` on selection/new without the
   * shell touching its internals. Omit it for the original page primitive.
   */
  sidebar?: SidebarSlot;
  /**
   * Opt into the mobile drawer behavior for the `sidebar`. Default `false` keeps
   * the sidebar a static column at every width. No effect without `sidebar`.
   */
  responsive?: boolean;
  /** Media query that switches the sidebar into drawer mode. Default `(max-width: 768px)`. */
  mobileQuery?: string;
  /** Desktop sidebar width (number → px). Default `280`. */
  sidebarWidth?: number | string;
  /** Accessible label for the drawer toggle. Default `Conversaciones`. */
  toggleLabel?: string;
  className?: string;
  style?: CSSProperties;
}

const TOGGLE_STYLE_ID = 'fi-aws-toggle-style';

function ensureToggleStyle(): void {
  if (typeof document === 'undefined') return;
  if (document.getElementById(TOGGLE_STYLE_ID)) return;
  const el = document.createElement('style');
  el.id = TOGGLE_STYLE_ID;
  el.textContent = `
    .fi-aws-toggle {
      display: inline-flex; align-items: center; justify-content: center;
      width: 44px; height: 44px; min-width: 44px; min-height: 44px; border-radius: 10px;
      border: 1px solid rgba(255,255,255,0.14);
      background: rgba(10,14,22,0.55);
      backdrop-filter: blur(var(--glass-blur-compact, 8px));
      color: #e2e8f0; cursor: pointer; padding: 0;
      transition: background 0.15s ease, border-color 0.15s ease;
    }
    .fi-aws-toggle:hover { background: rgba(255,255,255,0.08); }
    .fi-aws-toggle:active { background: rgba(255,255,255,0.12); }
    .fi-aws-toggle:focus-visible {
      outline: 2px solid var(--og-accent, #34d399); outline-offset: 2px;
    }
  `;
  document.head.appendChild(el);
}

export function AgentWorkspaceShell({
  visual = 'aurora',
  density = 'comfortable',
  header,
  conversation,
  rail,
  footer,
  sidebar,
  responsive = false,
  mobileQuery = '(max-width: 768px)',
  sidebarWidth = 280,
  toggleLabel = 'Conversaciones',
  className,
  style,
}: AgentWorkspaceShellProps) {
  useDensityStyle();
  const isMobile = useMediaQuery(mobileQuery);
  const [isOpen, setIsOpen] = useState(false);

  const hasSidebar = sidebar != null;
  const drawerMode = hasSidebar && responsive && isMobile;

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((v) => !v), []);

  // Resizing/rotating back to desktop must never strand an open drawer.
  useEffect(() => {
    if (!drawerMode && isOpen) setIsOpen(false);
  }, [drawerMode, isOpen]);

  // While the drawer is open: Escape closes it and the body scroll is locked so
  // the page behind doesn't produce a second scroll surface.
  useEffect(() => {
    if (!drawerMode || !isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false);
    };
    document.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [drawerMode, isOpen]);

  useEffect(() => {
    if (drawerMode) ensureToggleStyle();
  }, [drawerMode]);

  const rootStyle: CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    height: '100dvh',
    minHeight: 0,
    overflow: 'hidden',
    // B3-FIGLASS-MOBILE-NATIVE-1: on an installed iOS PWA running
    // `apple-mobile-web-app-status-bar-style: black-translucent`, the web view is
    // full-bleed UNDER the clock. Pad the top by the safe-area inset so the
    // content (sidebar top, header) sits below the status bar while the BACKGROUND
    // still reaches the physical top edge — the native look. box-sizing keeps the
    // padding inside the 100dvh so nothing overflows the bottom. env() resolves to
    // 0 everywhere else, so desktop and non-translucent installs are unchanged.
    boxSizing: 'border-box',
    paddingTop: 'env(safe-area-inset-top, 0px)',
  };

  const mainStyle: CSSProperties = {
    display: 'grid',
    gridTemplateColumns: rail ? 'minmax(0, 1fr) minmax(280px, 360px)' : 'minmax(0, 1fr)',
    flex: '1 1 auto',
    minHeight: 0,
    overflow: 'hidden',
  };

  const conversationStyle: CSSProperties = { minHeight: 0, overflow: 'hidden' };
  const railStyle: CSSProperties = { minHeight: 0, overflowY: 'auto' };

  const rootClassName = [
    'fi-agent-workspace',
    `fi-visual-${visual}`,
    `fi-density-${density}`,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  // The page-composition column (header / main grid / footer). When a sidebar is
  // present it fills the row beside the sidebar; otherwise it is the root and the
  // output stays byte-identical to the original FG-4 primitive.
  const content = (
    <div
      data-fi-workspace="agent"
      data-fi-visual={visual}
      data-fi-density={density}
      className={rootClassName}
      style={hasSidebar ? { ...rootStyle, flex: 1, minWidth: 0, height: '100%', ...style } : { ...rootStyle, ...style }}
    >
      {header != null && <header data-fi-slot="header">{header}</header>}
      <main data-fi-slot="main" style={mainStyle}>
        <div data-fi-slot="conversation" style={conversationStyle}>
          {conversation}
        </div>
        {rail != null && (
          <aside data-fi-slot="rail" style={railStyle}>
            {rail}
          </aside>
        )}
      </main>
      {footer != null && <footer data-fi-slot="footer">{footer}</footer>}
    </div>
  );

  if (!hasSidebar) return content;

  const api: AgentWorkspaceShellApi = { isOpen, isMobile, open, close, toggle };
  const sidebarNode = typeof sidebar === 'function' ? sidebar(api) : sidebar;

  const widthCss = typeof sidebarWidth === 'number' ? `${sidebarWidth}px` : sidebarWidth;

  const sidebarContainerStyle: CSSProperties = drawerMode
    ? {
        position: 'fixed',
        top: 0,
        left: 0,
        bottom: 0,
        zIndex: 50,
        width: `min(${widthCss}, 85vw)`,
        display: 'flex',
        flexDirection: 'column',
        transform: isOpen ? 'translateX(0)' : 'translateX(-100%)',
        transition: 'transform 0.24s ease',
        willChange: 'transform',
        containerType: 'inline-size',
        containerName: 'fi-sidebar',
        // The drawer owns a FULLY opaque surface: a consumer's sidebar may be a
        // translucent glass panel (fine over the static desktop rail), but as an
        // off-canvas layer even 3% translucency lets large bright conversation
        // text ghost through and the list loses contrast. Token-overridable.
        background: 'var(--fi-drawer-bg, rgb(10, 14, 22))',
        boxShadow: 'var(--fi-drawer-shadow, 0 0 40px rgba(0, 0, 0, 0.55))',
        // The drawer is fixed to the physical top, so its own content also needs
        // the status-bar inset when the PWA runs full-bleed (MOBILE-NATIVE-1).
        boxSizing: 'border-box',
        paddingTop: 'env(safe-area-inset-top, 0px)',
      }
    : {
        width: widthCss,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        containerType: 'inline-size',
        containerName: 'fi-sidebar',
      };

  return (
    <div
      data-fi-workspace="agent-with-sidebar"
      style={{ display: 'flex', height: '100dvh', position: 'relative', overflowX: 'hidden' }}
    >
      <nav
        data-fi-slot="sidebar"
        aria-label={toggleLabel}
        style={sidebarContainerStyle}
        aria-hidden={drawerMode ? !isOpen : undefined}
        inert={drawerMode && !isOpen ? true : undefined}
      >
        {sidebarNode}
      </nav>

      {drawerMode && (
        <div
          onClick={close}
          aria-hidden
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 40,
            background: 'rgba(0,0,0,0.5)',
            opacity: isOpen ? 1 : 0,
            pointerEvents: isOpen ? 'auto' : 'none',
            transition: 'opacity 0.24s ease',
          }}
        />
      )}

      {drawerMode && !isOpen && (
        <button
          type="button"
          className="fi-aws-toggle"
          onClick={open}
          aria-label={toggleLabel}
          aria-expanded={isOpen}
          style={{ position: 'absolute', top: '0.6rem', left: '0.6rem', zIndex: 30 }}
        >
          <Menu size={18} aria-hidden />
        </button>
      )}

      {content}
    </div>
  );
}
