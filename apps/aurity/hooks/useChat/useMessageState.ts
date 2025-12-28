/**
 * useMessageState Hook
 *
 * Manages core message state and refs.
 * SOLID: Single Responsibility - only state management.
 */

import { useState, useRef } from 'react';
import type { FIMessage, EmotionalAnalysis, BehaviorMetrics } from '@aurity-standalone/types/assistant';

export interface MessageStateReturn {
  // State
  messages: FIMessage[];
  setMessages: React.Dispatch<React.SetStateAction<FIMessage[]>>;
  loading: boolean;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  error: string | null;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
  isTyping: boolean;
  setIsTyping: React.Dispatch<React.SetStateAction<boolean>>;
  loadingInitial: boolean;
  setLoadingInitial: React.Dispatch<React.SetStateAction<boolean>>;
  lastEmotionalAnalysis: EmotionalAnalysis | null;
  setLastEmotionalAnalysis: React.Dispatch<React.SetStateAction<EmotionalAnalysis | null>>;

  // Refs
  lastMessageRef: React.MutableRefObject<string | null>;
  lastBehaviorMetricsRef: React.MutableRefObject<BehaviorMetrics | undefined>;
  introductionLoadedRef: React.MutableRefObject<boolean>;
  olderMessagesBufferRef: React.MutableRefObject<FIMessage[]>;
}

export function useMessageState(): MessageStateReturn {
  // Core state
  const [messages, setMessages] = useState<FIMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [loadingInitial, setLoadingInitial] = useState(true);
  const [lastEmotionalAnalysis, setLastEmotionalAnalysis] = useState<EmotionalAnalysis | null>(null);

  // Refs for retry and buffer
  const lastMessageRef = useRef<string | null>(null);
  const lastBehaviorMetricsRef = useRef<BehaviorMetrics | undefined>(undefined);
  const introductionLoadedRef = useRef(false);
  const olderMessagesBufferRef = useRef<FIMessage[]>([]);

  return {
    messages,
    setMessages,
    loading,
    setLoading,
    error,
    setError,
    isTyping,
    setIsTyping,
    loadingInitial,
    setLoadingInitial,
    lastEmotionalAnalysis,
    setLastEmotionalAnalysis,
    lastMessageRef,
    lastBehaviorMetricsRef,
    introductionLoadedRef,
    olderMessagesBufferRef,
  };
}
