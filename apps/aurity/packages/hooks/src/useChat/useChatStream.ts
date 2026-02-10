/**
 * useChatStream Hook - SSE Streaming for AI Chat
 *
 * Best Practices 2025-2026:
 * - Real-time streaming with status indicators
 * - Thinking/reasoning token support (event: meta)
 * - Stop/abort capability
 * - Throttled re-renders for performance
 *
 * @see https://ai-sdk.dev/docs/ai-sdk-ui/chatbot
 * Created: 2025-12-12
 */

import { useState, useRef, useCallback } from 'react';
import { api } from '@/lib/api/client';
import { ROUTES } from '@/lib/api/routes';

// ============================================================================
// Types
// ============================================================================

export type StreamStatus = 'idle' | 'connecting' | 'streaming' | 'thinking' | 'complete' | 'error' | 'aborted';

export interface StreamingMessage {
  id: string;
  role: 'assistant';
  content: string;
  thinking?: string;
  isStreaming: boolean;
  status: StreamStatus;
  timestamp: string;
}

export interface StreamRequest {
  messages: Array<{ role: string; content: string }>;
  user?: string;
  session_id?: string;
  behavior_metrics?: Record<string, unknown>;
}

export interface UseChatStreamOptions {
  /** Throttle re-renders (ms). Default: 50ms */
  throttleMs?: number;
  /** Callback when thinking content arrives */
  onThinking?: (thinking: string) => void;
  /** Callback when content chunk arrives */
  onContent?: (content: string) => void;
  /** Callback when stream completes */
  onComplete?: (message: StreamingMessage) => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

export interface UseChatStreamReturn {
  /** Current streaming message */
  streamingMessage: StreamingMessage | null;
  /** Stream status */
  status: StreamStatus;
  /** Start streaming a message */
  startStream: (request: StreamRequest) => Promise<StreamingMessage | null>;
  /** Abort current stream */
  stop: () => void;
  /** Reset state */
  reset: () => void;
}

// ============================================================================
// Constants
// ============================================================================

const STREAM_ENDPOINT = `${ROUTES.assistant}/chat/stream`;
const DEFAULT_THROTTLE_MS = 50;

// ============================================================================
// Hook Implementation
// ============================================================================

export function useChatStream(options: UseChatStreamOptions = {}): UseChatStreamReturn {
  const {
    throttleMs = DEFAULT_THROTTLE_MS,
    onThinking,
    onContent,
    onComplete,
    onError,
  } = options;

  const [status, setStatus] = useState<StreamStatus>('idle');
  const [streamingMessage, setStreamingMessage] = useState<StreamingMessage | null>(null);

  // Refs for abort control and throttling
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastUpdateRef = useRef<number>(0);
  const pendingContentRef = useRef<string>('');
  const pendingThinkingRef = useRef<string>('');

  // Throttled state update
  const flushPendingUpdates = useCallback(() => {
    setStreamingMessage(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        content: pendingContentRef.current,
        thinking: pendingThinkingRef.current || undefined,
      };
    });
  }, []);

  // Stop/abort stream
  const stop = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setStatus('aborted');
    flushPendingUpdates();
    setStreamingMessage(prev => prev ? { ...prev, isStreaming: false, status: 'aborted' } : null);
  }, [flushPendingUpdates]);

  // Reset state
  const reset = useCallback(() => {
    stop();
    setStatus('idle');
    setStreamingMessage(null);
    pendingContentRef.current = '';
    pendingThinkingRef.current = '';
  }, [stop]);

  // Parse SSE line
  const parseSSELine = useCallback((line: string): { event?: string; data?: string } | null => {
    if (!line.trim()) return null;

    if (line.startsWith('event:')) {
      return { event: line.slice(6).trim() };
    }
    if (line.startsWith('data:')) {
      return { data: line.slice(5).trim() };
    }
    return null;
  }, []);

  // Start streaming
  const startStream = useCallback(async (request: StreamRequest): Promise<StreamingMessage | null> => {
    // Abort any existing stream
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Initialize state
    const messageId = `stream-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
    const initialMessage: StreamingMessage = {
      id: messageId,
      role: 'assistant',
      content: '',
      isStreaming: true,
      status: 'connecting',
      timestamp: new Date().toISOString(),
    };

    setStreamingMessage(initialMessage);
    setStatus('connecting');
    pendingContentRef.current = '';
    pendingThinkingRef.current = '';

    // Create abort controller
    abortControllerRef.current = new AbortController();

    try {
      const response = await api.raw(STREAM_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify(request),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`Stream request failed: ${response.status} ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      setStatus('streaming');
      setStreamingMessage(prev => prev ? { ...prev, status: 'streaming' } : null);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentEvent = 'message'; // Default event type

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          const parsed = parseSSELine(line);
          if (!parsed) continue;

          if (parsed.event) {
            currentEvent = parsed.event;
          }

          if (parsed.data) {
            try {
              // Handle [DONE] signal
              if (parsed.data === '[DONE]') {
                continue;
              }

              const jsonData = JSON.parse(parsed.data);

              // Handle different event types
              if (currentEvent === 'meta' && jsonData.thinking) {
                // Thinking/reasoning content
                pendingThinkingRef.current += jsonData.thinking;
                setStatus('thinking');
                setStreamingMessage(prev => prev ? { ...prev, status: 'thinking' } : null);
                onThinking?.(pendingThinkingRef.current);
              } else if (jsonData.choices?.[0]?.delta?.content) {
                // Regular content chunk
                const chunk = jsonData.choices[0].delta.content;
                pendingContentRef.current += chunk;
                onContent?.(pendingContentRef.current);

                // Throttled update
                const now = Date.now();
                if (now - lastUpdateRef.current >= throttleMs) {
                  lastUpdateRef.current = now;
                  flushPendingUpdates();
                }
              }

              // Reset event type after processing data
              currentEvent = 'message';
            } catch {
              // Non-JSON data, likely plain text chunk
              if (currentEvent === 'meta') {
                pendingThinkingRef.current += parsed.data;
              } else {
                pendingContentRef.current += parsed.data;
              }
            }
          }
        }
      }

      // Final flush
      flushPendingUpdates();

      const finalMessage: StreamingMessage = {
        id: messageId,
        role: 'assistant',
        content: pendingContentRef.current,
        thinking: pendingThinkingRef.current || undefined,
        isStreaming: false,
        status: 'complete',
        timestamp: initialMessage.timestamp,
      };

      setStreamingMessage(finalMessage);
      setStatus('complete');
      onComplete?.(finalMessage);

      return finalMessage;
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        // Stream was intentionally aborted
        return null;
      }

      const err = error instanceof Error ? error : new Error('Unknown streaming error');
      setStatus('error');
      setStreamingMessage(prev => prev ? { ...prev, isStreaming: false, status: 'error' } : null);
      onError?.(err);

      return null;
    } finally {
      abortControllerRef.current = null;
    }
  }, [throttleMs, onThinking, onContent, onComplete, onError, parseSSELine, flushPendingUpdates]);

  return {
    streamingMessage,
    status,
    startStream,
    stop,
    reset,
  };
}
