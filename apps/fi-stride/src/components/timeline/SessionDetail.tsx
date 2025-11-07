/**
 * SessionDetail Component
 *
 * Panel detalle: carga eventos reales desde API y muestra EventStream
 *
 * Card: FI-UI-FEAT-202
 * Philosophy: Real data only, cache fallback on error
 */

'use client';

import React, { useEffect } from 'react';
import { useTimelineStore } from '@/ui/stores/timeline-store';
import { getSessionDetailAdapted } from '@/lib/api/timeline-adapter';
import { EventStream } from './EventStream';

export function SessionDetail() {
  const {
    selectedSessionId,
    sessionDetail,
    isLoadingDetail,
    error,
    setSessionDetail,
    setIsLoadingDetail,
    setError,
  } = useTimelineStore();

  useEffect(() => {
    if (!selectedSessionId) {
      setSessionDetail(null);
      return;
    }

    async function loadDetail() {
      setIsLoadingDetail(true);
      setError(null);

      try {
        const detail = await getSessionDetailAdapted(selectedSessionId!);
        setSessionDetail(detail);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to load session detail';
        setError(errorMsg);

        // Try to use cached detail if available
        // (cache logic already in timeline.ts with fallback)
      } finally {
        setIsLoadingDetail(false);
      }
    }

    loadDetail();
  }, [selectedSessionId]);

  if (!selectedSessionId) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <p className="text-lg text-slate-400 mb-2">Select a session</p>
          <p className="text-sm text-slate-500">Choose from the list to view events</p>
        </div>
      </div>
    );
  }

  if (isLoadingDetail) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-500 mx-auto mb-3"></div>
          <p className="text-sm text-slate-400">Loading events...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <p className="text-sm text-red-400 mb-4">⚠️ {error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 text-sm bg-slate-800 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!sessionDetail) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-sm text-slate-500">No session loaded</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 p-4 border-b border-slate-700 bg-slate-900/50">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-slate-100">
            Events ({sessionDetail.events.length})
          </h2>
          <div className="flex items-center gap-2">
            {sessionDetail.policy_badges.hash_verified === 'OK' && (
              <span className="text-xs text-emerald-400" title="Hash verified">
                ✓ Verified
              </span>
            )}
            {sessionDetail.size.interaction_count > 200 && (
              <span className="text-xs text-amber-400" title="Virtualized rendering">
                ⚡ Virtualized
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs text-slate-500">
          <span>{sessionDetail.auto_events_count} auto</span>
          <span>•</span>
          <span>{sessionDetail.manual_events_count} manual</span>
          <span>•</span>
          <span>{sessionDetail.size.total_tokens.toLocaleString()} tokens</span>
        </div>
      </div>

      {/* Event Stream */}
      <div className="flex-1 overflow-hidden">
        <EventStream />
      </div>
    </div>
  );
}
