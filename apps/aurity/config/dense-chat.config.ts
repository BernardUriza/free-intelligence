/**
 * Dense Chat Mode Configuration
 * 
 * Evidence-based design tokens for optimal readability:
 * - 50-75 CPL (characters per line), sweet spot ~66 CPL
 * - 100dvh viewport (mobile-safe)
 * - Safe area insets for notches
 * - WCAG contrast ≥4.5:1
 * - IntersectionObserver for infinite scroll
 */

export const denseChatConfig = {
  // Typography (evidence-based)
  typography: {
    maxCPL: 66, // Characters per line (50-75 range)
    minCPL: 50,
    lineHeight: 1.35, // Dense but readable
    bodySize: 'text-sm', // 14px
    metaSize: 'text-xs', // 12px
    bodyWeight: 'font-normal', // 400
    metaWeight: 'font-normal', // 400
  },

  // Spacing (ultra-compact)
  spacing: {
    gapY: 'gap-y-1', // 4px between messages
    dayDividerGap: 'my-3', // 12px around date separators
    containerPadding: 'px-4 py-2', // Horizontal 16px, Vertical 8px
  },

  // Viewport (mobile-safe)
  viewport: {
    height: 'h-[100dvh]', // Dynamic viewport height
    safeAreaTop: 'env(safe-area-inset-top)',
    safeAreaBottom: 'env(safe-area-inset-bottom)',
    safeAreaLeft: 'env(safe-area-inset-left)',
    safeAreaRight: 'env(safe-area-inset-right)',
  },

  // Colors (WCAG AA compliant)
  colors: {
    userText: 'text-slate-100', // ~95% opacity
    aiText: 'text-slate-50', // ~98% opacity
    metaText: 'text-slate-500', // Muted
    dividerLine: 'border-slate-800/50',
    dividerText: 'text-slate-600',
    background: 'bg-slate-950',
  },

  // Accessibility
  a11y: {
    containerRole: 'log', // Live region
    ariaLive: 'polite', // Implicit with role="log"
    itemRole: 'article',
  },

  // Infinite scroll
  infiniteScroll: {
    rootMargin: '100px', // Load more when 100px from top
    threshold: 0,
    batchSize: 20, // Load 20 messages at a time
  },

  // Autoscroll behavior
  autoscroll: {
    threshold: 100, // Auto-scroll if within 100px of bottom
    behavior: 'smooth' as ScrollBehavior,
  },
} as const;

/**
 * Calculate optimal container width for target CPL
 * 
 * Formula: width = CPL × avgCharWidth
 * avgCharWidth ≈ 0.5em for monospace, 0.45em for proportional
 */
export function getOptimalWidth(targetCPL: number = 66): string {
  // For text-sm (14px) with proportional font:
  // 66 CPL × 0.45em ≈ 29.7em ≈ 416px at 14px
  const emWidth = targetCPL * 0.45;
  return `${emWidth}em`; // e.g., "29.7em"
}

/**
 * Check if user is near bottom (for autoscroll)
 */
export function isNearBottom(
  element: HTMLElement,
  threshold: number = 100
): boolean {
  const { scrollHeight, scrollTop, clientHeight } = element;
  return scrollHeight - scrollTop - clientHeight < threshold;
}

/**
 * Preserve scroll position when prepending content
 */
export function preserveScrollPosition(
  element: HTMLElement,
  callback: () => void
): void {
  const previousScrollHeight = element.scrollHeight;
  const previousScrollTop = element.scrollTop;

  callback();

  // Restore position after content injection
  requestAnimationFrame(() => {
    const newScrollHeight = element.scrollHeight;
    const heightDiff = newScrollHeight - previousScrollHeight;
    element.scrollTop = previousScrollTop + heightDiff;
  });
}
