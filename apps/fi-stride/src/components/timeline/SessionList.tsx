/**
 * SessionList Component
 *
 * Master panel: lista de sesiones con selección
 *
 * Card: FI-UI-FEAT-202
 * Philosophy: Scroll estable, keyboard nav, sin layout shift
 */

'use client';

import React, { useEffect, useRef } from 'react';
import { useTimelineStore } from '@/ui/stores/timeline-store';
import { getSessionSummariesAdapted } from '@/lib/api/timeline-adapter';
import type { SessionSummary } from '@/lib/api/timeline';

export function SessionList() {
  const {
    sessions,
    selectedSessionId,
    isLoadingSessions,
    error,
    setSessions,
    setSelectedSessionId,
    setIsLoadingSessions,
    setError,
  } = useTimelineStore();

  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function loadSessions() {
      setIsLoadingSessions(true);
      setError(null);

      try {
        const data = await getSessionSummariesAdapted({ limit: 50, sort: 'recent' });
        setSessions(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load sessions');
      } finally {
        setIsLoadingSessions(false);
      }
    }

    loadSessions();
  }, []);

  const handleSessionClick = (session: SessionSummary) => {
    // Preserve scroll position before selection
    if (listRef.current) {
      const scrollTop = listRef.current.scrollTop;
      // Store scroll position for later restoration if needed
      sessionStorage.setItem('timeline_sessions_scroll', scrollTop.toString());
    }

    setSelectedSessionId(session.metadata.session_id);
  };

  const handleKeyDown = (event: React.KeyboardEvent, session: SessionSummary, index: number) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleSessionClick(session);
    } else if (event.key === 'ArrowDown') {
      event.preventDefault();
      const nextIndex = Math.min(index + 1, sessions.length - 1);
      const nextElement = document.querySelector(`[data-session-index="${nextIndex}"]`) as HTMLElement;
      nextElement?.focus();
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      const prevIndex = Math.max(index - 1, 0);
      const prevElement = document.querySelector(`[data-session-index="${prevIndex}"]`) as HTMLElement;
      prevElement?.focus();
    }
  };

  if (isLoadingSessions) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500 mx-auto mb-2"></div>
          <p className="text-xs text-slate-500">Loading sessions...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center p-4">
        <div className="text-center">
          <p className="text-sm text-red-400 mb-3">⚠️ {error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-3 py-1.5 text-xs bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-sm text-slate-500">No sessions found</p>
      </div>
    );
  }

  return (
    <div
      ref={listRef}
      role="listbox"
      aria-label="Session list"
      className="h-full overflow-y-auto overscroll-contain"
      style={{ scrollBehavior: 'smooth' }}
    >
      <div className="space-y-2 p-2">
        {sessions.map((session, index) => {
          const isSelected = session.metadata.session_id === selectedSessionId;

          return (
            <div
              key={session.metadata.session_id}
              data-session-index={index}
              role="option"
              aria-selected={isSelected}
              tabIndex={0}
              onClick={() => handleSessionClick(session)}
              onKeyDown={(e) => handleKeyDown(e, session, index)}
              className={`
                min-h-[72px] p-3 rounded-lg border cursor-pointer
                transition-all duration-150
                focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 focus:ring-offset-slate-950
                ${
                  isSelected
                    ? 'bg-emerald-950/30 border-emerald-700 ring-1 ring-emerald-900'
                    : 'bg-slate-900 border-slate-700 hover:bg-slate-800 hover:border-slate-600'
                }
              `}
            >
              {/* Session ID */}
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-mono text-slate-400 truncate">
                  {session.metadata.session_id.substring(0, 16)}...
                </span>
                <div className="flex items-center gap-1">
                  {session.policy_badges.hash_verified === 'OK' && (
                    <span className="text-emerald-500 text-xs" title="Hash verified">
                      ✓
                    </span>
                  )}
                  {session.policy_badges.audit_logged === 'OK' && (
                    <span className="text-blue-500 text-xs" title="Audit logged">
                      📝
                    </span>
                  )}
                </div>
              </div>

              {/* Preview */}
              <p className="text-sm text-slate-300 line-clamp-2 mb-2">{session.preview || 'No preview'}</p>

              {/* Stats */}
              <div className="flex items-center gap-3 text-xs text-slate-500">
                <span>{session.size.interaction_count} interactions</span>
                <span>•</span>
                <span>{session.timespan.duration_human}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
