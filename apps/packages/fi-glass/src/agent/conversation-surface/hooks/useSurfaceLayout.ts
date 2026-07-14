'use client';

/**
 * fi-glass · conversation-surface/useSurfaceLayout — how the surface sizes
 * itself.
 *
 * - `rootStyle` (FG-2): `"viewport"` keeps the full-page 100dvh
 *   (backward-compatible default); `"contained"` fills its parent cell and
 *   clips at the root so the transcript region scrolls internally, never the
 *   page.
 * - `contentInset` (B3-FIGLASS-15 + MOBILE-1): the fluid center cap lives on
 *   INNER content wrappers — never the scroll container — so the scrollbar
 *   renders at the viewport edge. On a phone the fixed 60px gutter starves the
 *   composer, so it collapses to a thin 16px gutter below the mobile
 *   breakpoint.
 */

import type { CSSProperties } from 'react';
import { useMediaQuery } from '../../../shell/useMediaQuery';
import type { AgentConversationSurfaceLayout } from '../types';

export interface SurfaceLayout {
  rootStyle: CSSProperties;
  contentInset: string;
}

export function useSurfaceLayout(layout: AgentConversationSurfaceLayout): SurfaceLayout {
  const isMobileViewport = useMediaQuery('(max-width: 768px)');
  // CONV-MOBILE-RECLAIM-1: on phones the regions already own a 12px gutter via
  // --fi-transcript-pad / --fi-composer-bar-px, so an extra inset here would
  // double-charge the viewport. Full width below the breakpoint.
  const contentInset = isMobileViewport ? '100%' : 'calc(100% - 60px)';
  const rootStyle: CSSProperties =
    layout === 'contained'
      ? { display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0, overflow: 'hidden' }
      : { display: 'flex', flexDirection: 'column', height: '100dvh' };
  return { rootStyle, contentInset };
}
