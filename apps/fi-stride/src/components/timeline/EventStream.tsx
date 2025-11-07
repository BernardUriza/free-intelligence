/**
 * EventStream Component
 *
 * Lista de eventos con virtualización automática (>200 eventos)
 * Scroll estable con anchor preservation
 *
 * Card: FI-UI-FEAT-202
 * Philosophy: Performance is UX, scroll is sacred
 */

'use client';

import React, { useRef, useMemo, useEffect } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useTimelineStore } from '@/ui/stores/timeline-store';
import type { EventResponse } from '@/lib/api/timeline';

const ITEM_HEIGHT = 56; // Fixed height for virtualization
const VIRTUALIZATION_THRESHOLD = 200;

interface EventsByDate {
  date: string;
  events: EventResponse[];
}

export function EventStream() {
  const { events, isVirtualized, selectedSessionId, setScrollAnchor } = useTimelineStore();

  const parentRef = useRef<HTMLDivElement>(null);
  const previousScrollTop = useRef<number>(0);

  // Group events by date (memoized)
  const eventsByDate = useMemo<EventsByDate[]>(() => {
    const groups = new Map<string, EventResponse[]>();

    events.forEach((event) => {
      const date = new Date(event.timestamp).toISOString().split('T')[0];
      if (!groups.has(date)) {
        groups.set(date, []);
      }
      groups.get(date)!.push(event);
    });

    return Array.from(groups.entries())
      .map(([date, events]) => ({ date, events }))
      .sort((a, b) => b.date.localeCompare(a.date)); // Most recent first
  }, [events]);

  // Flatten events with date headers for virtualization
  const virtualItems = useMemo(() => {
    const items: Array<{ type: 'header' | 'event'; data: any; id: string }> = [];

    eventsByDate.forEach((group) => {
      items.push({ type: 'header', data: group.date, id: `header-${group.date}` });
      group.events.forEach((event) => {
        items.push({ type: 'event', data: event, id: event.event_id });
      });
    });

    return items;
  }, [eventsByDate]);

  // Virtualizer (only if >200 events)
  const virtualizer = useVirtualizer({
    count: virtualItems.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ITEM_HEIGHT,
    overscan: 8,
    enabled: isVirtualized,
  });

  // Capture scroll anchor before updates
  useEffect(() => {
    if (!parentRef.current || !selectedSessionId) return;

    const handleScroll = () => {
      if (!parentRef.current) return;

      const scrollTop = parentRef.current.scrollTop;
      previousScrollTop.current = scrollTop;

      // Find first visible event
      const firstVisible = virtualItems.find((item) => {
        const element = document.querySelector(`[data-event-id="${item.id}"]`);
        if (!element) return false;

        const rect = element.getBoundingClientRect();
        const parentRect = parentRef.current!.getBoundingClientRect();

        return rect.top >= parentRect.top && rect.top <= parentRect.bottom;
      });

      if (firstVisible && firstVisible.type === 'event') {
        const element = document.querySelector(`[data-event-id="${firstVisible.id}"]`);
        if (element) {
          const parentRect = parentRef.current!.getBoundingClientRect();
          const rect = element.getBoundingClientRect();
          const offset = rect.top - parentRect.top;

          setScrollAnchor(selectedSessionId, {
            eventId: firstVisible.id,
            offset,
          });
        }
      }
    };

    const parent = parentRef.current;
    parent.addEventListener('scroll', handleScroll, { passive: true });

    return () => parent.removeEventListener('scroll', handleScroll);
  }, [selectedSessionId, virtualItems, setScrollAnchor]);

  if (events.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-sm text-slate-500">No events</p>
      </div>
    );
  }

  return (
    <div ref={parentRef} className="h-full overflow-y-auto overscroll-contain" style={{ scrollBehavior: 'smooth' }}>
      <div style={{ height: isVirtualized ? `${virtualizer.getTotalSize()}px` : 'auto', position: 'relative' }}>
        {isVirtualized ? (
          // Virtualized rendering
          virtualizer.getVirtualItems().map((virtualRow) => {
            const item = virtualItems[virtualRow.index];

            return (
              <div
                key={virtualRow.key}
                data-event-id={item.id}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                {item.type === 'header' ? (
                  <DateHeader date={item.data} />
                ) : (
                  <EventCard event={item.data} />
                )}
              </div>
            );
          })
        ) : (
          // Non-virtualized rendering
          <div className="space-y-2 p-2">
            {eventsByDate.map((group) => (
              <div key={group.date}>
                <DateHeader date={group.date} />
                {group.events.map((event) => (
                  <div key={event.event_id} data-event-id={event.event_id}>
                    <EventCard event={event} />
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function DateHeader({ date }: { date: string }) {
  return (
    <div className="sticky top-0 z-10 bg-slate-950/95 backdrop-blur-sm px-2 py-2">
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">{date}</h3>
    </div>
  );
}

function EventCard({ event }: { event: EventResponse }) {
  const time = new Date(event.timestamp).toLocaleTimeString();

  return (
    <div className="min-h-[56px] p-3 mb-2 rounded-lg bg-slate-900 border border-slate-700 hover:bg-slate-800 transition-colors">
      <div className="flex items-start justify-between mb-1">
        <span className="text-sm font-medium text-slate-300">{event.event_type.replace(/_/g, ' ')}</span>
        <span className="text-xs text-slate-500">{time}</span>
      </div>

      <p className="text-sm text-slate-400 line-clamp-2">{event.what}</p>

      {event.summary && event.summary !== event.what && (
        <p className="text-xs text-slate-500 mt-1">{event.summary}</p>
      )}

      <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
        <span>{event.who}</span>
        {event.auto_generated && <span className="text-amber-500">auto</span>}
        {event.tags && event.tags.length > 0 && (
          <div className="flex gap-1">
            {event.tags.slice(0, 2).map((tag) => (
              <span key={tag} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
