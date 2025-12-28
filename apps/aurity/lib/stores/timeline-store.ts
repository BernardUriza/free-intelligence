/**
 * Timeline Store (Zustand)
 *
 * Manages timeline state: sessions, selected session, events, scroll anchors
 *
 * Card: FI-UI-FEAT-202
 * Philosophy: Determinism visible, state minimal, derivation maximal
 */

import { create } from 'zustand';
import type { SessionSummary, SessionDetail, EventResponse } from '@aurity-standalone/api-client/timeline';

export interface ScrollAnchor {
  eventId: string;
  offset: number;
}

export interface TimelineState {
  // Data
  sessions: SessionSummary[];
  selectedSessionId: string | null;
  sessionDetail: SessionDetail | null;
  events: EventResponse[];

  // UI State
  isVirtualized: boolean;
  scrollAnchors: Record<string, ScrollAnchor>; // sessionId -> anchor

  // Loading & Errors
  isLoadingSessions: boolean;
  isLoadingDetail: boolean;
  error: string | null;

  // Actions
  setSessions: (sessions: SessionSummary[]) => void;
  setSelectedSessionId: (id: string | null) => void;
  setSessionDetail: (detail: SessionDetail | null) => void;
  setEvents: (events: EventResponse[]) => void;
  setIsVirtualized: (value: boolean) => void;
  setScrollAnchor: (sessionId: string, anchor: ScrollAnchor) => void;
  getScrollAnchor: (sessionId: string) => ScrollAnchor | null;
  setIsLoadingSessions: (value: boolean) => void;
  setIsLoadingDetail: (value: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  sessions: [],
  selectedSessionId: null,
  sessionDetail: null,
  events: [],
  isVirtualized: false,
  scrollAnchors: {},
  isLoadingSessions: false,
  isLoadingDetail: false,
  error: null,
};

export const useTimelineStore = create<TimelineState>((set, get) => ({
  ...initialState,

  setSessions: (sessions) => set({ sessions }),

  setSelectedSessionId: (id) => set({ selectedSessionId: id }),

  setSessionDetail: (detail) => {
    set({ sessionDetail: detail });
    if (detail) {
      const events = detail.events || [];
      set({
        events,
        isVirtualized: events.length > 200,
      });
    }
  },

  setEvents: (events) => set({ events }),

  setIsVirtualized: (value) => set({ isVirtualized: value }),

  setScrollAnchor: (sessionId, anchor) =>
    set((state) => ({
      scrollAnchors: { ...state.scrollAnchors, [sessionId]: anchor },
    })),

  getScrollAnchor: (sessionId) => get().scrollAnchors[sessionId] || null,

  setIsLoadingSessions: (value) => set({ isLoadingSessions: value }),

  setIsLoadingDetail: (value) => set({ isLoadingDetail: value }),

  setError: (error) => set({ error }),

  reset: () => set(initialState),
}));
