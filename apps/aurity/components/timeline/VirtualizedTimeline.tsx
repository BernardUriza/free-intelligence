/**
 * VirtualizedTimeline Component
 *
 * High-performance virtualized list for timeline events.
 * Uses @tanstack/react-virtual for efficient rendering.
 *
 * Features:
 * - Renders only visible items
 * - Smooth scrolling
 * - Dynamic item heights
 * - Supports 10,000+ events
 *
 * Created: 2025-12-08
 */

'use client';

import React, { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { EventTimeline, type TimelineEvent } from '@/components/audit/EventTimeline';
import { memoryConfig } from '@/lib/memory-config';
import { Loader2 } from 'lucide-react';

interface VirtualizedTimelineProps {
  events: TimelineEvent[];
  isLoading?: boolean;
  onLoadMore?: () => void;
  hasMore?: boolean;
  className?: string;
}

export function VirtualizedTimeline({
  events,
  isLoading = false,
  onLoadMore,
  hasMore = false,
  className = '',
}: VirtualizedTimelineProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: events.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 150, // Estimated height of each event card
    overscan: 5, // Render 5 extra items above/below viewport
  });

  const items = virtualizer.getVirtualItems();

  // Trigger load more when scrolling near bottom
  React.useEffect(() => {
    const [lastItem] = [...items].reverse();

    if (!lastItem) return;

    if (
      lastItem.index >= events.length - 5 &&
      hasMore &&
      !isLoading &&
      onLoadMore
    ) {
      onLoadMore();
    }
  }, [hasMore, isLoading, items, onLoadMore, events.length]);

  if (events.length === 0 && !isLoading) {
    return (
      <div className={`text-center py-12 ${className}`}>
        <p className="text-slate-400 text-sm">
          No se encontraron eventos.
        </p>
      </div>
    );
  }

  return (
    <div
      ref={parentRef}
      className={`overflow-auto ${className}`}
      style={{ maxHeight: '600px' }}
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {items.map((virtualItem) => {
          const event = events[virtualItem.index];
          
          return (
            <div
              key={event.id}
              data-index={virtualItem.index}
              ref={virtualizer.measureElement}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${virtualItem.start}px)`,
              }}
            >
              <EventTimeline
                events={[event]}
                config={memoryConfig}
                isLoading={false}
                error={null}
                className="pb-0"
              />
            </div>
          );
        })}
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="animate-spin h-6 w-6 text-emerald-500 mr-2" />
          <span className="fi-subtitle">Cargando más eventos...</span>
        </div>
      )}
    </div>
  );
}
