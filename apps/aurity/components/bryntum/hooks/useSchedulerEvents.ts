/**
 * useSchedulerEvents Hook
 * 
 * Manages event handlers and interactions for Bryntum SchedulerPro.
 * Provides keyboard shortcuts, event clicks, and custom behaviors.
 */

import { useEffect, useCallback } from 'react';
import type { BryntumSchedulerInstance, UnifiedEvent } from '../types/scheduler.types';

interface UseSchedulerEventsProps {
  instance: BryntumSchedulerInstance | null;
  onEventClick?: (event: UnifiedEvent) => void;
  onNavigatePrev?: () => void;
  onNavigateNext?: () => void;
  onZoomIn?: () => void;
  onZoomOut?: () => void;
  onGoToToday?: () => void;
  onEscape?: () => void;
}

export function useSchedulerEvents({
  instance,
  onEventClick,
  onNavigatePrev,
  onNavigateNext,
  onZoomIn,
  onZoomOut,
  onGoToToday,
  onEscape,
}: UseSchedulerEventsProps): void {
  /**
   * Handle Bryntum event clicks
   */
  const handleBryntumEventClick = useCallback(
    (bryntumEvent: { eventRecord: { data: { originalEvent?: UnifiedEvent } } }) => {
      const originalEvent = bryntumEvent.eventRecord.data.originalEvent;
      
      if (originalEvent && onEventClick) {
        onEventClick(originalEvent);
      }
    },
    [onEventClick]
  );

  /**
   * Attach Bryntum event listener
   */
  useEffect(() => {
    if (!instance || !onEventClick) return;

    // Add event listener to instance
    // @ts-expect-error - Bryntum API
    instance.on?.('eventClick', handleBryntumEventClick);

    return () => {
      // @ts-expect-error - Bryntum API
      instance.un?.('eventClick', handleBryntumEventClick);
    };
  }, [instance, handleBryntumEventClick, onEventClick]);

  /**
   * Keyboard shortcuts
   */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if in input field
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      switch (e.key) {
        case 'ArrowLeft':
          if (e.shiftKey && onNavigatePrev) {
            e.preventDefault();
            onNavigatePrev();
          }
          break;

        case 'ArrowRight':
          if (e.shiftKey && onNavigateNext) {
            e.preventDefault();
            onNavigateNext();
          }
          break;

        case '+':
        case '=':
          if (onZoomIn) {
            e.preventDefault();
            onZoomIn();
          }
          break;

        case '-':
          if (onZoomOut) {
            e.preventDefault();
            onZoomOut();
          }
          break;

        case 't':
        case 'T':
          if (onGoToToday) {
            e.preventDefault();
            onGoToToday();
          }
          break;

        case 'Escape':
          if (onEscape) {
            e.preventDefault();
            onEscape();
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [
    onNavigatePrev,
    onNavigateNext,
    onZoomIn,
    onZoomOut,
    onGoToToday,
    onEscape,
  ]);
}
