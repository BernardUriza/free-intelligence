/**
 * useChatKeyboardNav Hook
 *
 * SOLID Principles:
 * - S: Only handles keyboard navigation for chat containers
 * - D: Receives scroll functions as dependencies, doesn't import them
 *
 * Keyboard Shortcuts:
 * - End: Scroll to bottom
 * - Home: Scroll to top + trigger load more
 * - PageDown: Scroll down 80% viewport
 * - PageUp: Scroll up 80% viewport
 */

import { useCallback } from 'react';

export interface UseChatKeyboardNavOptions {
  /** Ref to scrollable container */
  containerRef: React.RefObject<HTMLDivElement>;
  /** Function to scroll to bottom */
  scrollToBottom: (behavior?: ScrollBehavior) => void;
  /** Function to load more messages */
  onLoadMore?: () => void;
  /** Are there more messages to load? */
  hasMore?: boolean;
  /** Viewport scroll percentage (default 0.8 = 80%) */
  viewportScrollPercent?: number;
}

export interface UseChatKeyboardNavReturn {
  /** Keyboard event handler to attach to container */
  handleKeyDown: (e: React.KeyboardEvent) => void;
}

export function useChatKeyboardNav({
  containerRef,
  scrollToBottom,
  onLoadMore,
  hasMore = false,
  viewportScrollPercent = 0.8,
}: UseChatKeyboardNavOptions): UseChatKeyboardNavReturn {
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const container = containerRef.current;
      if (!container) return;

      switch (e.key) {
        case 'End':
          // End key → scroll to bottom
          e.preventDefault();
          scrollToBottom('smooth');
          break;

        case 'Home':
          // Home key → scroll to top (and load more if available)
          e.preventDefault();
          container.scrollTo({ top: 0, behavior: 'smooth' });
          if (hasMore && onLoadMore) {
            onLoadMore();
          }
          break;

        case 'PageDown':
          // PageDown → scroll down one viewport
          e.preventDefault();
          container.scrollBy({
            top: container.clientHeight * viewportScrollPercent,
            behavior: 'smooth',
          });
          break;

        case 'PageUp':
          // PageUp → scroll up one viewport
          e.preventDefault();
          container.scrollBy({
            top: -container.clientHeight * viewportScrollPercent,
            behavior: 'smooth',
          });
          break;

        // Allow default behavior for other keys
        default:
          break;
      }
    },
    [containerRef, scrollToBottom, onLoadMore, hasMore, viewportScrollPercent]
  );

  return { handleKeyDown };
}
