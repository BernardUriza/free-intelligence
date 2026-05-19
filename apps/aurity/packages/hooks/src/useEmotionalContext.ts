/**
 * useEmotionalContext - React Hook for Emotional Intelligence System
 *
 * Tracks user interactions and detects emotional states:
 * - frustrated: User experiencing difficulties
 * - successful: User progressing well
 * - hesitant: User uncertain or stuck
 * - neutral: Normal interaction
 *
 * Privacy-first: All data stays in LocalStorage.
 *
 * Card: FI-ONBOARD-005
 * Author: Bernard Uriza Orozco
 */

'use client';

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import type { FITone } from '@aurity-standalone/types/assistant';
import {
  type EmotionalState,
  type InteractionEvent,
  type EmotionalMetrics,
  type EmotionalDetectionConfig,
  DEFAULT_CONFIG,
  calculateMetrics,
  detectEmotionalState,
  saveEvent,
  getEvents,
  clearEvents,
  saveState,
  getState,
  emotionalStateToTone,
  getToneSuggestion,
} from '@/lib/emotional-detection';

// ============================================================================
// Types
// ============================================================================

export interface EmotionalContextValue {
  /** Current detected emotional state */
  emotionalState: EmotionalState;
  /** Confidence score (0-1) */
  confidence: number;
  /** Reason for current state detection */
  reason: string;
  /** Suggested FI tone based on emotional state */
  suggestedTone: FITone;
  /** Tone suggestion message for FI */
  toneSuggestion: string;
  /** Current metrics */
  metrics: EmotionalMetrics | null;
  /** Track a click event */
  trackClick: (target?: string) => void;
  /** Track a message sent */
  trackMessage: (content: string) => void;
  /** Track an error */
  trackError: (errorType?: string) => void;
  /** Track a success */
  trackSuccess: (successType?: string) => void;
  /** Track navigation */
  trackNavigation: (direction: 'forward' | 'back', phase?: string) => void;
  /** Track hover (for hesitation detection) */
  trackHover: (target: string, duration: number) => void;
  /** Reset emotional tracking */
  reset: () => void;
  /** Force recalculation */
  recalculate: () => void;
}

export interface UseEmotionalContextOptions {
  /** Custom configuration */
  config?: Partial<EmotionalDetectionConfig>;
  /** Recalculation interval in ms (default: 5000) */
  recalculateInterval?: number;
  /** Enable debug logging */
  debug?: boolean;
  /** Current phase for context */
  currentPhase?: string;
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useEmotionalContext(
  options: UseEmotionalContextOptions = {}
): EmotionalContextValue {
  const {
    config: customConfig,
    recalculateInterval = 5000,
    debug = false,
    currentPhase,
  } = options;

  // Memoize config to prevent infinite re-renders
  // Use JSON.stringify for deep comparison since customConfig is an object
  const configKey = JSON.stringify(customConfig);
  const config = useMemo(
    () => ({ ...DEFAULT_CONFIG, ...customConfig }),
    
    [configKey]
  );

  // State
  const [emotionalState, setEmotionalState] = useState<EmotionalState>('neutral');
  const [confidence, setConfidence] = useState(0);
  const [reason, setReason] = useState('Initializing...');
  const [metrics, setMetrics] = useState<EmotionalMetrics | null>(null);

  // Refs for tracking
  const lastMessageRef = useRef<string>('');
  const lastClickTimeRef = useRef<number>(0);

  // Debug logger (uses createLogger internally)
  const emotionalLog = useMemo(() => {
    const { createLogger } = require('@/lib/internal/logger');
    return createLogger('EmotionalContext');
  }, []);

  const log = useCallback(
    (message: string, data?: any) => {
      if (debug) {
        emotionalLog.debug(message, data || {});
      }
    },
    [debug, emotionalLog]
  );

  // Recalculate emotional state
  const recalculate = useCallback(() => {
    const events = getEvents();
    const newMetrics = calculateMetrics(events, config);
    const detection = detectEmotionalState(newMetrics, config);

    setMetrics(newMetrics);
    setEmotionalState(detection.state);
    setConfidence(detection.confidence);
    setReason(detection.reason);
    saveState(detection.state);

    log('Recalculated', { state: detection.state, confidence: detection.confidence, reason: detection.reason });
  }, [config, log]);

  // Track click event
  const trackClick = useCallback(
    (target?: string) => {
      const now = Date.now();
      const event: InteractionEvent = {
        type: 'click',
        timestamp: now,
        metadata: {
          target,
          phase: currentPhase,
        },
      };

      // Detect rapid clicks
      if (now - lastClickTimeRef.current < 500) {
        log('Rapid click detected');
      }
      lastClickTimeRef.current = now;

      saveEvent(event);
      recalculate();
    },
    [currentPhase, recalculate, log]
  );

  // Track message sent
  const trackMessage = useCallback(
    (content: string) => {
      const isRepeated = content === lastMessageRef.current;
      lastMessageRef.current = content;

      const event: InteractionEvent = {
        type: 'message',
        timestamp: Date.now(),
        metadata: {
          repeated: isRepeated,
          phase: currentPhase,
        },
      };

      if (isRepeated) {
        log('Repeated message detected');
      }

      saveEvent(event);
      recalculate();
    },
    [currentPhase, recalculate, log]
  );

  // Track error
  const trackError = useCallback(
    (errorType?: string) => {
      const event: InteractionEvent = {
        type: 'error',
        timestamp: Date.now(),
        metadata: {
          target: errorType,
          phase: currentPhase,
        },
      };

      log('Error tracked', errorType);
      saveEvent(event);
      recalculate();
    },
    [currentPhase, recalculate, log]
  );

  // Track success
  const trackSuccess = useCallback(
    (successType?: string) => {
      const event: InteractionEvent = {
        type: 'success',
        timestamp: Date.now(),
        metadata: {
          target: successType,
          phase: currentPhase,
        },
      };

      log('Success tracked', successType);
      saveEvent(event);
      recalculate();
    },
    [currentPhase, recalculate, log]
  );

  // Track navigation
  const trackNavigation = useCallback(
    (direction: 'forward' | 'back', phase?: string) => {
      const event: InteractionEvent = {
        type: 'navigation',
        timestamp: Date.now(),
        metadata: {
          target: direction,
          phase: phase || currentPhase,
        },
      };

      log('Navigation tracked', direction);
      saveEvent(event);
      recalculate();
    },
    [currentPhase, recalculate, log]
  );

  // Track hover (for hesitation)
  const trackHover = useCallback(
    (target: string, duration: number) => {
      // Only track long hovers (> 3 seconds)
      if (duration < 3000) return;

      const event: InteractionEvent = {
        type: 'hover',
        timestamp: Date.now(),
        metadata: {
          target,
          duration,
          phase: currentPhase,
        },
      };

      log('Long hover tracked', { target, duration });
      saveEvent(event);
      recalculate();
    },
    [currentPhase, recalculate, log]
  );

  // Reset all tracking
  const reset = useCallback(() => {
    clearEvents();
    setEmotionalState('neutral');
    setConfidence(0);
    setReason('Reset');
    setMetrics(null);
    lastMessageRef.current = '';
    lastClickTimeRef.current = 0;
    log('Emotional tracking reset');
  }, [log]);

  // Initialize from localStorage and set up interval
  useEffect(() => {
    // Load initial state
    const savedState = getState();
    setEmotionalState(savedState);

    // Initial calculation
    recalculate();

    // Set up periodic recalculation for idle detection
    const interval = setInterval(() => {
      recalculate();
    }, recalculateInterval);

    return () => clearInterval(interval);
  }, [recalculate, recalculateInterval]);

  // Track idle time
  useEffect(() => {
    const handleActivity = () => {
      const event: InteractionEvent = {
        type: 'idle',
        timestamp: Date.now(),
        metadata: { phase: currentPhase },
      };
      saveEvent(event);
    };

    // Reset idle timer on any interaction
    const events = ['mousedown', 'keydown', 'touchstart', 'scroll'];
    events.forEach((event) => {
      window.addEventListener(event, handleActivity, { passive: true });
    });

    return () => {
      events.forEach((event) => {
        window.removeEventListener(event, handleActivity);
      });
    };
  }, [currentPhase]);

  return {
    emotionalState,
    confidence,
    reason,
    suggestedTone: emotionalStateToTone(emotionalState),
    toneSuggestion: getToneSuggestion(emotionalState),
    metrics,
    trackClick,
    trackMessage,
    trackError,
    trackSuccess,
    trackNavigation,
    trackHover,
    reset,
    recalculate,
  };
}

// ============================================================================
// Convenience Exports
// ============================================================================

export type { EmotionalState, InteractionEvent, EmotionalMetrics };
export { emotionalStateToTone, getToneSuggestion };
