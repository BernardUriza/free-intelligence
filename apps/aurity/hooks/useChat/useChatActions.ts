/**
 * useChatActions Hook
 *
 * Handles chat actions: send message, get introduction, retry, clear.
 * SOLID: Single Responsibility - only action handlers.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  assistantApi,
  BackendUnavailableError,
  type StreamController,
} from '@aurity-standalone/api-client/assistant';
import type {
  FIMessage,
  BehaviorMetrics,
  OnboardingPhase,
  FITone,
} from '@aurity-standalone/types/assistant';
import type { IMessageStorage } from '@/lib/chat/storage';
import { generateMessageId, isConnectionError } from './utils';
import type { FIChatResponse, StreamingState } from './types';

export interface UseChatActionsOptions {
  phase?: OnboardingPhase;
  context: Record<string, unknown>;
  storageKey?: string;
  autoIntroduction: boolean;
  /** Enable model thinking/reasoning (Qwen3). Default true. Set false to save compute. */
  enableThinking?: boolean;
  storage: IMessageStorage;

  // State
  messages: FIMessage[];
  loadingInitial: boolean;

  // State setters
  setMessages: React.Dispatch<React.SetStateAction<FIMessage[]>>;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
  setIsTyping: React.Dispatch<React.SetStateAction<boolean>>;
  setLastEmotionalAnalysis: React.Dispatch<React.SetStateAction<any>>;
  setHasMoreMessages: React.Dispatch<React.SetStateAction<boolean>>;
  setPaginationOffset: React.Dispatch<React.SetStateAction<number>>;

  // Refs
  lastMessageRef: React.MutableRefObject<string | null>;
  lastBehaviorMetricsRef: React.MutableRefObject<BehaviorMetrics | undefined>;
  introductionLoadedRef: React.MutableRefObject<boolean>;
  olderMessagesBufferRef: React.MutableRefObject<FIMessage[]>;
}

export interface UseChatActionsReturn {
  sendMessage: (message: string, behaviorMetrics?: BehaviorMetrics) => Promise<FIChatResponse | null>;
  sendMessageStream: (message: string, behaviorMetrics?: BehaviorMetrics) => Promise<FIChatResponse | null>;
  getIntroduction: () => Promise<FIChatResponse | null>;
  clearConversation: () => void;
  retry: () => Promise<void>;
  stopStream: () => void;
  streaming: StreamingState;
}

export function useChatActions({
  phase,
  context,
  storageKey,
  autoIntroduction,
  enableThinking = true, // Default: enable thinking (Qwen3 reasoning)
  storage,
  messages,
  loadingInitial,
  setMessages,
  setLoading,
  setError,
  setIsTyping,
  setLastEmotionalAnalysis,
  setHasMoreMessages,
  setPaginationOffset,
  lastMessageRef,
  lastBehaviorMetricsRef,
  introductionLoadedRef,
  olderMessagesBufferRef,
}: UseChatActionsOptions): UseChatActionsReturn {
  // ========================================================================
  // Streaming State (2025-2026 Best Practices)
  // ========================================================================
  const [streaming, setStreaming] = useState<StreamingState>({
    status: 'idle',
    content: '',
    thinking: '',
    isStreaming: false,
  });

  const streamControllerRef = useRef<StreamController | null>(null);
  const [, setStreamUpdateCounter] = useState(0);  // Force re-renders for each chunk

  // Stop stream
  const stopStream = useCallback(() => {
    if (streamControllerRef.current) {
      streamControllerRef.current.abort();
      streamControllerRef.current = null;
    }
    setStreaming(prev => ({
      ...prev,
      status: 'aborted',
      isStreaming: false,
    }));
  }, []);

  // Reset streaming state
  const resetStreaming = useCallback(() => {
    setStreaming({
      status: 'idle',
      content: '',
      thinking: '',
      isStreaming: false,
    });
  }, []);

  // ========================================================================
  // Get Introduction
  // ========================================================================
  const getIntroduction = useCallback(async (): Promise<FIChatResponse | null> => {
    setLoading(true);
    setError(null);
    setIsTyping(true);

    try {
      const response = await assistantApi.introduction({
        ...context,
        phase,
      });

      const introMsgId = generateMessageId('intro');

      const fiMessage: FIMessage = {
        role: 'assistant',
        content: response.message,
        timestamp: new Date().toISOString(),
        metadata: {
          tone: response.persona as FITone,
          phase,
          id: introMsgId,
          voice: response.voice,
        },
      };

      setMessages(prev => prev.length === 0 ? [fiMessage] : prev);
      setIsTyping(false);
      setLoading(false);
      return response;
    } catch (err) {
      if (err instanceof BackendUnavailableError || isConnectionError(err)) {
        setIsTyping(false);
        setLoading(false);
        return null;
      }

      const errorMessage = err instanceof Error ? err.message : 'Failed to get introduction';
      setError(errorMessage);
      setIsTyping(false);
      setLoading(false);
      return null;
    }
  }, [phase, context, setMessages, setLoading, setError, setIsTyping]);

  // ========================================================================
  // Auto-Introduction
  // ========================================================================
  useEffect(() => {
    if (!loadingInitial && autoIntroduction && !introductionLoadedRef.current && messages.length === 0) {
      introductionLoadedRef.current = true;
      getIntroduction();
    }
  }, [autoIntroduction, messages.length, loadingInitial, getIntroduction, introductionLoadedRef]);

  // ========================================================================
  // Send Message
  // ========================================================================
  const sendMessage = useCallback(async (
    userMessage: string,
    behaviorMetrics?: BehaviorMetrics
  ): Promise<FIChatResponse | null> => {
    if (!userMessage.trim()) return null;

    setLoading(true);
    setError(null);
    lastMessageRef.current = userMessage;
    lastBehaviorMetricsRef.current = behaviorMetrics;

    const userMsgId = generateMessageId('user');

    const userMsg: FIMessage = {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
      metadata: { phase, id: userMsgId },
    };

    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);

    try {
      const response = await assistantApi.chat({
        message: userMessage,
        context: { ...context, phase },
        conversationHistory: messages,
        doctor_id: context?.doctor_id as string,
        session_id: storageKey || 'unknown',
        behavior_metrics: behaviorMetrics,
        enable_thinking: enableThinking, // Toggle model thinking/reasoning (Qwen3)
        response_mode: context?.response_mode as string | undefined, // concise vs explanatory
      });

      if (response.emotional_analysis) {
        setLastEmotionalAnalysis(response.emotional_analysis);
      }

      const assistantMsgId = generateMessageId('assistant');

      const fiMessage: FIMessage = {
        role: 'assistant',
        content: response.message,
        thinking: response.thinking || undefined,  // Qwen3 thinking at root level
        timestamp: new Date().toISOString(),
        metadata: {
          tone: response.persona as FITone,
          phase,
          id: assistantMsgId,
          voice: response.voice,
        },
      };

      setMessages(prev => {
        const exists = prev.some(m =>
          m.role === 'assistant' && m.content.trim() === response.message.trim()
        );
        if (exists) return prev;
        return [...prev, fiMessage];
      });

      setIsTyping(false);
      setLoading(false);
      return response;
    } catch (err) {
      setIsTyping(false);
      setLoading(false);

      // Handle offline/connection errors gracefully
      if (err instanceof BackendUnavailableError || isConnectionError(err)) {
        const offlineMsg: FIMessage = {
          role: 'assistant',
          content: '⚠️ No se pudo conectar al servidor. Tu mensaje se guardó localmente.',
          timestamp: new Date().toISOString(),
          metadata: { tone: 'neutral' as FITone, phase, id: generateMessageId('offline') },
        };
        setMessages(prev => [...prev, offlineMsg]);
        return null;
      }

      // Handle other errors
      const errorMessage = err instanceof Error ? err.message : 'Failed to send message';
      setError(errorMessage);

      const errorMsg: FIMessage = {
        role: 'assistant',
        content: `❌ Error: ${errorMessage}. Click "Retry" to try again.`,
        timestamp: new Date().toISOString(),
        metadata: { tone: 'neutral' as FITone, phase, id: generateMessageId('error') },
      };
      setMessages(prev => [...prev, errorMsg]);
      return null;
    }
  }, [phase, context, messages, storageKey, enableThinking, setMessages, setLoading, setError, setIsTyping, setLastEmotionalAnalysis, lastMessageRef, lastBehaviorMetricsRef]);

  // ========================================================================
  // Send Message with Streaming (2025-2026 Best Practices)
  // ========================================================================
  const sendMessageStream = useCallback(async (
    userMessage: string,
    behaviorMetrics?: BehaviorMetrics
  ): Promise<FIChatResponse | null> => {
    if (!userMessage.trim()) return null;

    // Stop any existing stream
    stopStream();
    resetStreaming();

    setLoading(true);
    setError(null);
    lastMessageRef.current = userMessage;
    lastBehaviorMetricsRef.current = behaviorMetrics;

    const userMsgId = generateMessageId('user');

    const userMsg: FIMessage = {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
      metadata: { phase, id: userMsgId },
    };

    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);

    // Initialize streaming state
    setStreaming({
      status: 'connecting',
      content: '',
      thinking: '',
      isStreaming: true,
    });

    return new Promise((resolve) => {
      let finalContent = '';
      let finalThinking = '';

      console.log('[useChatActions.sendMessageStream] 🚀 Starting stream with context:', {
        persona: context?.persona,
        phase,
        messages: messages.length,
      });

      console.log('[useChatActions] 🚀 Starting stream with sendMessageStream');

      streamControllerRef.current = assistantApi.chatStream(
        {
          message: userMessage,
          context: { ...context, phase },
          conversationHistory: messages,
          doctor_id: context?.doctor_id as string,
          session_id: storageKey || 'unknown',
          behavior_metrics: behaviorMetrics,
          enable_thinking: enableThinking, // Toggle model thinking/reasoning (Qwen3)
          response_mode: context?.response_mode as string | undefined, // concise vs explanatory
        },
        {
          onThinking: (thinking) => {
            console.log('[useChatActions] 💭 onThinking callback called:', thinking.substring(0, 50));
            finalThinking = thinking;
            setStreamUpdateCounter(c => c + 1);  // Increment to ensure re-render
            setStreaming(prev => {
              const updated: StreamingState = {
                ...prev,
                status: 'thinking' as const,
                thinking,
                isStreaming: true,
              };
              console.log('[useChatActions] 💭 Updated streaming state:', { isStreaming: updated.isStreaming, thinkingLength: updated.thinking.length });
              return updated;
            });
          },
          onContent: (content) => {
            console.log('[useChatActions] 📝 onContent callback called:', content.substring(0, 50), '| Length:', content.length);
            finalContent = content;
            setStreamUpdateCounter(c => c + 1);  // Increment to ensure re-render (fixes React batching)
            setStreaming(prev => {
              const updated: StreamingState = {
                ...prev,
                status: 'streaming' as const,
                content,
                isStreaming: true,
              };
              console.log('[useChatActions] 📝 Updated streaming state:', { isStreaming: updated.isStreaming, contentLength: updated.content.length });
              return updated;
            });
          },
          onComplete: (response) => {
            console.log('[useChatActions] ✅ onComplete callback called:', {
              messageLength: response.message.length,
              hasThinking: !!response.thinking,
              model: (response as any).model,
            });
            streamControllerRef.current = null;

            // Create final message with thinking at root level (2025-2026 best practice)
            const assistantMsgId = generateMessageId('assistant');
            const fiMessage: FIMessage = {
              role: 'assistant',
              content: response.message,
              thinking: response.thinking || undefined,  // Qwen3 thinking at root level
              timestamp: new Date().toISOString(),
              metadata: {
                tone: response.persona as FITone,
                phase,
                id: assistantMsgId,
                voice: response.voice,
              },
            };

            setMessages(prev => {
              const exists = prev.some(m =>
                m.role === 'assistant' && m.content.trim() === response.message.trim()
              );
              if (exists) return prev;
              return [...prev, fiMessage];
            });

            setStreaming({
              status: 'complete',
              content: response.message,
              thinking: response.thinking || '',
              isStreaming: false,
            });

            setIsTyping(false);
            setLoading(false);
            resolve(response);
          },
          onError: (error) => {
            streamControllerRef.current = null;

            setStreaming(prev => ({
              ...prev,
              status: 'error',
              isStreaming: false,
            }));

            setIsTyping(false);
            setLoading(false);

            const errorMessage = error.message || 'Stream failed';
            setError(errorMessage);

            const errorMsg: FIMessage = {
              role: 'assistant',
              content: `❌ Error: ${errorMessage}. Click "Retry" to try again.`,
              timestamp: new Date().toISOString(),
              metadata: { tone: 'neutral' as FITone, phase, id: generateMessageId('error') },
            };
            setMessages(prev => [...prev, errorMsg]);
            resolve(null);
          },
          onAbort: () => {
            streamControllerRef.current = null;

            // If we got content before abort, save it
            if (finalContent) {
              const assistantMsgId = generateMessageId('assistant');
              const fiMessage: FIMessage = {
                role: 'assistant',
                content: finalContent,
                thinking: finalThinking || undefined,  // FIX: at root level (was in metadata)
                timestamp: new Date().toISOString(),
                metadata: {
                  tone: 'neutral' as FITone,
                  phase,
                  id: assistantMsgId,
                },
              };
              setMessages(prev => [...prev, fiMessage]);
            }

            setStreaming(prev => ({
              ...prev,
              status: 'aborted',
              isStreaming: false,
            }));

            setIsTyping(false);
            setLoading(false);
            resolve(null);
          },
        }
      );
    });
  }, [phase, context, messages, storageKey, enableThinking, setMessages, setLoading, setError, setIsTyping, lastMessageRef, lastBehaviorMetricsRef, stopStream, resetStreaming]);

  // ========================================================================
  // Retry
  // ========================================================================
  const retry = useCallback(async (): Promise<void> => {
    if (!lastMessageRef.current) return;

    setMessages(prev => prev.slice(0, -1));
    await sendMessage(lastMessageRef.current, lastBehaviorMetricsRef.current);
  }, [sendMessage, setMessages, lastMessageRef, lastBehaviorMetricsRef]);

  // ========================================================================
  // Clear Conversation
  // ========================================================================
  const clearConversation = useCallback(() => {
    setMessages([]);
    setError(null);
    setLoading(false);
    setIsTyping(false);
    lastMessageRef.current = null;
    olderMessagesBufferRef.current = [];
    setHasMoreMessages(false);
    setPaginationOffset(0);

    if (storageKey) {
      storage.clear(storageKey);
    }
  }, [storageKey, storage, setMessages, setError, setLoading, setIsTyping, setHasMoreMessages, setPaginationOffset, lastMessageRef, olderMessagesBufferRef]);

  // ========================================================================
  // Save Messages to Storage
  // ========================================================================
  useEffect(() => {
    if (storageKey && messages.length > 0) {
      storage.save(storageKey, messages);
    }
  }, [storageKey, messages, storage]);

  return {
    sendMessage,
    sendMessageStream,
    getIntroduction,
    clearConversation,
    retry,
    stopStream,
    streaming,
  };
}
