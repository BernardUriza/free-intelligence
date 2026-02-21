/** List view section — header + VirtualizedTimeline. */

'use client';

import React from 'react';
import { List } from 'lucide-react';
import { VirtualizedTimeline } from '@/components/timeline/VirtualizedTimeline';
import type { TimelineEvent } from '@/components/audit/EventTimeline';
import type { ViewType } from '../types';

interface TimelineListSectionProps {
  events: TimelineEvent[];
  viewType: ViewType;
  searchQuery: string;
  isLoadingMore: boolean;
  hasMore: boolean;
  onLoadMore: () => Promise<void>;
}

export function TimelineListSection({
  events,
  viewType,
  searchQuery,
  isLoadingMore,
  hasMore,
  onLoadMore,
}: TimelineListSectionProps) {
  if (events.length === 0) return null;

  return (
    <div className="tl-list-container">
      {viewType === 'both' && (
        <div className="tl-list-header fi-border-bottom">
          <List className="tl-list-icon" />
          <span className="fi-title-sm-medium">Lista de Eventos</span>
          <span className="fi-text-xs">({events.length} eventos)</span>
          {searchQuery && (
            <span className="tl-search-badge fi-text-success">
              &middot; Búsqueda: &quot;{searchQuery}&quot;
            </span>
          )}
        </div>
      )}

      <VirtualizedTimeline
        events={events}
        isLoading={isLoadingMore}
        onLoadMore={onLoadMore}
        hasMore={hasMore}
        className=""
      />
    </div>
  );
}
