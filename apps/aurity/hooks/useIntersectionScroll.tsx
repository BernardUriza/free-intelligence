/**
 * useIntersectionScroll Hook
 *
 * Uses Intersection Observer API for efficient scroll position detection.
 * More performant than scroll events for detecting top/bottom visibility.
 *
 * Features:
 * - Detects when user reaches top (load more) or bottom (scroll indicator)
 * - Zero scroll event listeners - uses native browser API
 * - Supports threshold configuration for early trigger
 *
 * References:
 * - https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API
 * - https://virtuoso.dev/react-intersection-observer/
 */

import { useEffect, useRef, useState, forwardRef } from 'react';
import type { ReactNode, CSSProperties } from 'react';

// ============================================================================
// TYPES
// ============================================================================

export interface UseIntersectionScrollOptions {
  /** Callback when top sentinel becomes visible */
  onTopVisible?: () => void;
  /** Callback when bottom sentinel becomes visible */
  onBottomVisible?: () => void;
  /** Root margin for early trigger (e.g., "100px" triggers 100px before visible) */
  rootMargin?: string;
  /** Threshold for intersection (0-1, where 0 = any part visible) */
  threshold?: number;
  /** Is loading at top (prevents multiple triggers) */
  loadingTop?: boolean;
  /** Is loading at bottom (prevents multiple triggers) */
  loadingBottom?: boolean;
  /** Disabled state */
  disabled?: boolean;
}

export interface UseIntersectionScrollReturn {
  /** Ref to attach to the scroll container */
  containerRef: React.RefObject<HTMLDivElement>;
  /** Ref for the top sentinel element */
  topSentinelRef: React.RefObject<HTMLDivElement>;
  /** Ref for the bottom sentinel element */
  bottomSentinelRef: React.RefObject<HTMLDivElement>;
  /** Is top currently visible */
  isTopVisible: boolean;
  /** Is bottom currently visible */
  isBottomVisible: boolean;
}

// ============================================================================
// HOOK IMPLEMENTATION
// ============================================================================

export function useIntersectionScroll({
  onTopVisible,
  onBottomVisible,
  rootMargin = '100px',
  threshold = 0,
  loadingTop = false,
  loadingBottom = false,
  disabled = false,
}: UseIntersectionScrollOptions = {}): UseIntersectionScrollReturn {
  const containerRef = useRef<HTMLDivElement>(null);
  const topSentinelRef = useRef<HTMLDivElement>(null);
  const bottomSentinelRef = useRef<HTMLDivElement>(null);

  const [isTopVisible, setIsTopVisible] = useState(false);
  const [isBottomVisible, setIsBottomVisible] = useState(true);

  // Stable callback refs
  const onTopVisibleRef = useRef(onTopVisible);
  const onBottomVisibleRef = useRef(onBottomVisible);
  onTopVisibleRef.current = onTopVisible;
  onBottomVisibleRef.current = onBottomVisible;

  useEffect(() => {
    if (disabled) return;

    const container = containerRef.current;
    const topSentinel = topSentinelRef.current;
    const bottomSentinel = bottomSentinelRef.current;

    if (!container) return;

    // Create observer
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.target === topSentinel) {
            setIsTopVisible(entry.isIntersecting);
            if (entry.isIntersecting && !loadingTop && onTopVisibleRef.current) {
              onTopVisibleRef.current();
            }
          }

          if (entry.target === bottomSentinel) {
            setIsBottomVisible(entry.isIntersecting);
            if (entry.isIntersecting && !loadingBottom && onBottomVisibleRef.current) {
              onBottomVisibleRef.current();
            }
          }
        });
      },
      {
        root: container,
        rootMargin,
        threshold,
      }
    );

    // Observe sentinels
    if (topSentinel) observer.observe(topSentinel);
    if (bottomSentinel) observer.observe(bottomSentinel);

    return () => observer.disconnect();
  }, [disabled, rootMargin, threshold, loadingTop, loadingBottom]);

  return {
    containerRef,
    topSentinelRef,
    bottomSentinelRef,
    isTopVisible,
    isBottomVisible,
  };
}

// ============================================================================
// SENTINEL COMPONENTS (invisible elements to observe)
// ============================================================================

export interface ScrollSentinelProps {
  /** Position of sentinel */
  position: 'top' | 'bottom';
  /** Height of sentinel (affects trigger distance) */
  height?: number;
  /** Debug mode - shows visible sentinel */
  debug?: boolean;
}

/**
 * ScrollSentinel - Invisible element for Intersection Observer to watch
 *
 * Place at the top/bottom of your scroll container.
 * When this element becomes visible, it triggers the corresponding callback.
 */
export const ScrollSentinel = forwardRef<HTMLDivElement, ScrollSentinelProps>(
  function ScrollSentinel({ position, height = 1, debug = false }, ref) {
    return (
      <div
        ref={ref}
        style={{ height: `${height}px` }}
        className={`
          w-full shrink-0
          ${debug ? 'bg-red-500/20' : ''}
        `}
        aria-hidden="true"
        data-scroll-sentinel={position}
      />
    );
  }
);

// ============================================================================
// INFINITE SCROLL CONTAINER
// ============================================================================

export interface InfiniteScrollContainerProps {
  children: ReactNode;
  /** Callback to load more items at top */
  onLoadMore?: () => void;
  /** Is currently loading more */
  isLoading?: boolean;
  /** Has more items to load */
  hasMore?: boolean;
  /** Loading indicator component */
  loadingIndicator?: ReactNode;
  /** Custom className */
  className?: string;
  /** Custom style */
  style?: CSSProperties;
  /** Load more trigger margin (how early to trigger) */
  triggerMargin?: string;
}

/**
 * InfiniteScrollContainer - Self-contained infinite scroll component
 *
 * Combines useIntersectionScroll with sentinel elements.
 * Just wrap your content and provide onLoadMore callback.
 *
 * @example
 * ```tsx
 * <InfiniteScrollContainer
 *   onLoadMore={loadOlderMessages}
 *   isLoading={loading}
 *   hasMore={hasMoreMessages}
 * >
 *   {messages.map(msg => <Message key={msg.id} {...msg} />)}
 * </InfiniteScrollContainer>
 * ```
 */
export function InfiniteScrollContainer({
  children,
  onLoadMore,
  isLoading = false,
  hasMore = true,
  loadingIndicator,
  className = '',
  style,
  triggerMargin = '200px',
}: InfiniteScrollContainerProps) {
  const {
    containerRef,
    topSentinelRef,
    bottomSentinelRef,
  } = useIntersectionScroll({
    onTopVisible: hasMore ? onLoadMore : undefined,
    loadingTop: isLoading,
    rootMargin: triggerMargin,
  });

  return (
    <div
      ref={containerRef}
      className={`overflow-y-auto ${className}`}
      style={style}
    >
      {/* Top Sentinel */}
      <ScrollSentinel ref={topSentinelRef} position="top" />

      {/* Loading indicator */}
      {isLoading && loadingIndicator}

      {/* Content */}
      {children}

      {/* Bottom Sentinel */}
      <ScrollSentinel ref={bottomSentinelRef} position="bottom" />
    </div>
  );
}
