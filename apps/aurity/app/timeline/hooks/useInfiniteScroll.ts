/** Hook: IntersectionObserver-based infinite scroll trigger. */

import { useEffect, useRef } from 'react';

interface UseInfiniteScrollOptions {
  hasMore: boolean;
  isLoading: boolean;
  isLoadingMore: boolean;
  loadMore: () => void;
  threshold?: number;
  rootMargin?: string;
}

/**
 * Returns a ref to attach to a sentinel element. When the sentinel
 * enters the viewport and more data is available, `loadMore` fires.
 */
export function useInfiniteScroll({
  hasMore,
  isLoading,
  isLoadingMore,
  loadMore,
  threshold = 0.1,
  rootMargin = '100px',
}: UseInfiniteScrollOptions) {
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined' || !('IntersectionObserver' in window)) {
      return;
    }

    const el = sentinelRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && hasMore && !isLoading && !isLoadingMore) {
          loadMore();
        }
      },
      { threshold, rootMargin },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore, isLoading, isLoadingMore, loadMore, threshold, rootMargin]);

  return sentinelRef;
}
