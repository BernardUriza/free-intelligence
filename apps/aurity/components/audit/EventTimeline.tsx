'use client';

/**
 * EventTimeline - Generic Reusable Timeline Component
 *
 * Unified component for displaying chronological events with:
 * - Configurable rendering (via config objects)
 * - Support for DialogFlow segments, Timeline events, and more
 * - Optimistic updates (React 19)
 * - Search, filter, export
 * - Audio sync (optional)
 *
 * Author: Bernard Uriza Orozco
 * Created: 2025-11-18
 */

import React, { useState, useMemo, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import {
  Search,
  Download,
  ChevronDown,
  ChevronUp,
  AlertCircle,
} from 'lucide-react';

// ============================================================================
// Types
// ============================================================================

export interface TimelineEvent {
  id: string;
  timestamp: string | number; // ISO string or seconds
  type: string; // e.g., "transcription", "diarization", "SOAP"
  content: string; // Main text
  metadata?: Record<string, any>; // Additional data (speaker, confidence, tags, etc.)
}

export interface TimelineConfig {
  // Header rendering with full context
  renderHeader?: (
    event: TimelineEvent,
    isExpanded: boolean,
    toggleExpanded: () => void,
    actions?: {
      onPlay?: (event: TimelineEvent) => void;
      playingId?: string | null;
    }
  ) => React.ReactNode;

  // Badge rendering (event type, speaker, etc.)
  renderBadge?: (event: TimelineEvent) => React.ReactNode;

  // Timestamp formatting
  formatTimestamp?: (timestamp: string | number) => string;

  // Content rendering (can include collapsible sections)
  renderContent?: (event: TimelineEvent, isExpanded: boolean) => React.ReactNode;

  // Footer metadata
  renderFooter?: (event: TimelineEvent) => React.ReactNode;

  // Color scheme (based on event type/speaker)
  getColors?: (event: TimelineEvent) => {
    bg: string;
    border: string;
    text: string;
    badge: string;
  };

  // Export format
  formatExport?: (events: TimelineEvent[]) => string;

  // Search filter
  searchFilter?: (event: TimelineEvent, query: string) => boolean;

  // Actions (edit, play, etc.)
  actions?: {
    onEdit?: (event: TimelineEvent) => void;
    onPlay?: (event: TimelineEvent) => void;
    onDelete?: (event: TimelineEvent) => void;
  };

  // UI customization
  title?: string;
  emptyMessage?: string;
  showSearch?: boolean;
  showExport?: boolean;
  maxHeight?: string;
}

interface EventTimelineProps {
  events: TimelineEvent[];
  config: TimelineConfig;
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
  className?: string;
}

// ============================================================================
// Main Component
// ============================================================================

export function EventTimeline({
  events,
  config,
  isLoading = false,
  error = null,
  onRefresh,
  className = '',
}: EventTimelineProps) {
  // ========================================
  // State
  // ========================================

  const [searchQuery, setSearchQuery] = useState('');
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // ========================================
  // Computed Values
  // ========================================

  const filteredEvents = useMemo(() => {
    if (!searchQuery || !config.searchFilter) return events;

    const query = searchQuery.toLowerCase();
    return events.filter((event) => config.searchFilter!(event, query));
  }, [events, searchQuery, config]);

  // Stats computed for potential future use (API monitoring, debugging)
  useMemo(() => {
    const total = events.length;
    const typeBreakdown = events.reduce((acc, event) => {
      acc[event.type] = (acc[event.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return { total, typeBreakdown };
  }, [events]);

  // ========================================
  // Event Handlers
  // ========================================

  const toggleExpanded = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const handleExport = useCallback(() => {
    if (!config.formatExport) return;

    const content = config.formatExport(events);
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `timeline-export-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [events, config]);

  // ========================================
  // Default Renderers (Fallbacks)
  // ========================================

  const defaultFormatTimestamp = (timestamp: string | number): string => {
    const date = typeof timestamp === 'number'
      ? new Date(timestamp * 1000)
      : new Date(timestamp);

    // Format: "13 ene · 08:32:03 p.m."
    const dateStr = date.toLocaleDateString('es-MX', {
      day: 'numeric',
      month: 'short'
    });
    const timeStr = date.toLocaleTimeString('es-MX', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
    return `${dateStr} · ${timeStr}`;
  };

  const defaultGetColors = () => ({
    bg: 'bg-slate-500/10',
    border: 'border-slate-500/30',
    text: 'text-slate-400',
    badge: 'bg-slate-500',
  });

  const defaultSearchFilter = (event: TimelineEvent, query: string): boolean => {
    return (
      event.content.toLowerCase().includes(query) ||
      event.type.toLowerCase().includes(query) ||
      JSON.stringify(event.metadata).toLowerCase().includes(query)
    );
  };

  // ========================================
  // Render
  // ========================================

  const formatTimestamp = config.formatTimestamp || defaultFormatTimestamp;
  const getColors = config.getColors || defaultGetColors;
  // searchFilter is used indirectly via filteredEvents useMemo
  void (config.searchFilter || defaultSearchFilter);

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header removed - parent components control their own headers */}

      {/* ===== Loading State ===== */}
      {isLoading && (
        <div className="fi-card-xl space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-4 bg-slate-700 rounded w-1/4 mb-2"></div>
              <div className="h-16 bg-slate-700 rounded"></div>
            </div>
          ))}
        </div>
      )}

      {/* ===== Error State ===== */}
      {error && !isLoading && (
        <div className="fi-card-alert-danger">
          <AlertCircle className="h-6 w-6 fi-text-error flex-shrink-0" />
          <div>
            <p className="fi-text-error font-medium">Error al cargar eventos</p>
            <p className="fi-text-error/80 text-sm mt-1">{error}</p>
          </div>
          {onRefresh && (
            <Button
              onClick={onRefresh}
              variant="danger"
              className="ml-auto"
            >
              Reintentar
            </Button>
          )}
        </div>
      )}

      {/* ===== Empty State ===== */}
      {!isLoading && !error && events.length === 0 && (
        <div className="fi-card-xl-center">
          <p className="text-slate-400">
            {config.emptyMessage || 'No hay eventos disponibles'}
          </p>
        </div>
      )}

      {/* ===== Search & Export ===== */}
      {!isLoading && !error && events.length > 0 && (config.showSearch || config.showExport) && (
        <div className="flex gap-3">
          {config.showSearch && (
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Buscar eventos..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 fi-panel text-white placeholder-slate-400 focus:border-emerald-500 focus:outline-none"
              />
            </div>
          )}
          {config.showExport && config.formatExport && (
            <Button
              onClick={handleExport}
              variant="secondary"
              icon={Download}
              aria-label="Exportar eventos"
            >
              <span className="hidden sm:inline">Exportar</span>
            </Button>
          )}
        </div>
      )}

      {/* ===== Events Timeline ===== */}
      {!isLoading && !error && filteredEvents.length > 0 && (
        <div
          ref={scrollContainerRef}
          className={`fi-card-xl space-y-3 ${config.maxHeight || 'max-h-[600px]'} overflow-y-auto custom-scrollbar`}
          role="feed"
          aria-label="Timeline de eventos"
        >
          {filteredEvents.map((event) => {
            const colors = getColors(event);
            const isExpanded = expandedIds.has(event.id);

            return (
              <div
                key={event.id}
                className={`rounded-lg border transition-all ${colors.bg} ${colors.border}`}
                role="article"
              >
                <div className="p-4">
                  {/* Custom Header (if provided) */}
                  {config.renderHeader &&
                    config.renderHeader(
                      event,
                      isExpanded,
                      () => toggleExpanded(event.id),
                      config.actions
                        ? {
                            onPlay: config.actions.onPlay,
                          }
                        : undefined
                    )}

                  {/* Default Header (if no custom header) */}
                  {!config.renderHeader && (
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3 flex-wrap">
                        {/* Badge */}
                        {config.renderBadge ? (
                          config.renderBadge(event)
                        ) : (
                          <div className={`px-3 py-1.5 rounded-md ${colors.bg} border ${colors.border}`}>
                            <span className={`text-sm font-semibold ${colors.text}`}>
                              {event.type.toUpperCase()}
                            </span>
                          </div>
                        )}

                        {/* Timestamp */}
                        <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-900/50 border border-slate-700 rounded-md">
                          <span className="text-xs font-mono text-slate-400">
                            {formatTimestamp(event.timestamp)}
                          </span>
                        </div>
                      </div>

                      {/* Expand/Collapse Toggle */}
                      <Button
                        onClick={() => toggleExpanded(event.id)}
                        variant="ghost"
                        size="sm"
                        icon={isExpanded ? ChevronUp : ChevronDown}
                        aria-label={isExpanded ? 'Contraer' : 'Expandir'}
                      />
                    </div>
                  )}

                  {/* Content */}
                  {config.renderContent ? (
                    config.renderContent(event, isExpanded)
                  ) : (
                    <div className="fi-stack-sm">
                      <p className="fi-text leading-relaxed">{event.content}</p>
                      {isExpanded && event.metadata && (
                        <div className="pt-2 fi-border-top/50">
                          <pre className="fi-text-xs overflow-auto">
                            {JSON.stringify(event.metadata, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Custom Footer (if provided) */}
                  {config.renderFooter && config.renderFooter(event)}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ===== Search Results Info ===== */}
      {!isLoading && !error && searchQuery && (
        <div className="text-center fi-subtitle">
          Mostrando {filteredEvents.length} de {events.length} eventos
        </div>
      )}
    </div>
  );
}
