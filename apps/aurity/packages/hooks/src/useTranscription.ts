/**
 * useTranscription Hook
 *
 * Manages transcription state with streaming updates and highlight animation.
 * Handles both real-time chunk updates and final transcription display.
 *
 * Features:
 * - Streaming transcript accumulation
 * - Last chunk highlighting for visual feedback
 * - Word count calculation
 * - Auto-clearing of highlight after 3s
 *
 * Extracted from ConversationCapture during refactoring incremental.
 *
 * @example
 * const { transcriptionData, lastChunkText, addChunk, reset } = useTranscription();
 *
 * // Add a new transcription chunk
 * addChunk("Hello world");
 *
 * // Reset everything
 * reset();
 */

import { useState, useRef, useCallback, useEffect } from 'react';

export interface TranscriptionData {
  text: string;
  speakers?: Array<{ speaker: string; text: string; timestamp?: string }>;
  soapNote?: {
    subjective: string;
    objective: string;
    assessment: string;
    plan: string;
  };
}

interface UseTranscriptionReturn {
  transcriptionData: TranscriptionData;
  lastChunkText: string;
  addChunk: (text: string) => void;
  reset: () => void;
  getText: () => string;
  getWordCount: () => number;
}

export function useTranscription(): UseTranscriptionReturn {
  // State
  const [transcriptionData, setTranscriptionData] = useState<TranscriptionData>({ text: '' });
  const [lastChunkText, setLastChunkText] = useState<string>('');

  // Refs
  const streamingTranscriptRef = useRef<string>('');
  const highlightTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Add a new chunk to the transcript
  const addChunk = useCallback((text: string) => {
    if (!text) return;

    // Accumulate in ref (source of truth)
    streamingTranscriptRef.current += ' ' + text;

    // Update UI state
    setTranscriptionData({
      text: streamingTranscriptRef.current.trim(),
    });

    // Set highlight for animation (will auto-clear after 3s)
    setLastChunkText(text);

    // Clear previous timeout if exists
    if (highlightTimeoutRef.current) {
      clearTimeout(highlightTimeoutRef.current);
    }

    // Auto-clear highlight after 3s
    highlightTimeoutRef.current = setTimeout(() => {
      setLastChunkText('');
    }, 3000);
  }, []);

  // Reset all transcription state
  const reset = useCallback(() => {
    streamingTranscriptRef.current = '';
    setTranscriptionData({ text: '' });
    setLastChunkText('');

    if (highlightTimeoutRef.current) {
      clearTimeout(highlightTimeoutRef.current);
      highlightTimeoutRef.current = null;
    }
  }, []);

  // Get current transcript text
  const getText = useCallback(() => {
    return streamingTranscriptRef.current.trim();
  }, []);

  // Get word count
  const getWordCount = useCallback(() => {
    const text = streamingTranscriptRef.current.trim();
    if (!text) return 0;
    return text.split(/\s+/).filter((w) => w.length > 0).length;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (highlightTimeoutRef.current) {
        clearTimeout(highlightTimeoutRef.current);
      }
    };
  }, []);

  return {
    transcriptionData,
    lastChunkText,
    addChunk,
    reset,
    getText,
    getWordCount,
  };
}
