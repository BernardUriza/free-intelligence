/** Header actions bar — view toggle + refresh button. */

'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { BarChart3, List, RefreshCw } from 'lucide-react';
import type { ViewType } from '../types';

interface TimelineHeaderActionsProps {
  viewType: ViewType;
  onViewTypeChange: (view: ViewType) => void;
  isLoading: boolean;
  onRefresh: () => void;
}

export function TimelineHeaderActions({
  viewType,
  onViewTypeChange,
  isLoading,
  onRefresh,
}: TimelineHeaderActionsProps) {
  return (
    <div className="tl-header-actions">
      {/* View Mode Toggle */}
      <div className="tl-view-toggle-group">
        <Button
          onClick={() => onViewTypeChange('scheduler')}
          className={
            viewType === 'scheduler'
              ? 'fi-view-toggle-active'
              : 'fi-view-toggle'
          }
          variant="ghost"
          size="sm"
          title="Vista Scheduler"
        >
          <BarChart3 className="tl-icon-sm" />
          <span className="tl-responsive-label">Visual</span>
        </Button>

        <Button
          onClick={() => onViewTypeChange('list')}
          className={
            viewType === 'list' ? 'fi-view-toggle-active' : 'fi-view-toggle'
          }
          variant="ghost"
          size="sm"
          title="Vista Lista"
        >
          <List className="tl-icon-sm" />
          <span className="tl-responsive-label">Lista</span>
        </Button>

        <Button
          onClick={() => onViewTypeChange('both')}
          className={
            viewType === 'both' ? 'fi-view-toggle-active' : 'fi-view-toggle'
          }
          variant="ghost"
          size="sm"
          title="Ambas vistas"
        >
          <span className="tl-responsive-label">Ambas</span>
          <span className="tl-responsive-label-inverse">2</span>
        </Button>
      </div>

      {/* Refresh */}
      <Button
        onClick={onRefresh}
        disabled={isLoading}
        className="fi-btn-refresh"
        variant="ghost"
        size="sm"
        title="Refresh"
      >
        <RefreshCw
          className={isLoading ? 'tl-refresh-icon-spinning' : 'tl-refresh-icon'}
        />
        Refresh
      </Button>
    </div>
  );
}
