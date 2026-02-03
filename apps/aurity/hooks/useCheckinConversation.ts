/**
 * useCheckinConversation - Hook for FI Receptionist check-in flow
 *
 * Card: FI-CHECKIN-005
 * Connects to the OpenAI-compatible assistant chat endpoint:
 * - POST /api/aurity/assistant/chat
 *
 * Uses OpenAI Chat Completions format with AURITY extensions:
 * - messages: Array of {role, content}
 * - persona: receptionist
 * - session_id for conversation continuity
 * - Maintains state-machine approach with quick replies
 */

import { useState, useCallback, useRef } from 'react';
import type { FIMessage } from '@aurity-standalone/types/assistant';

// =============================================================================
// TYPES
// =============================================================================

export interface ConversationState {
  /** Current state in check-in flow */
  state:
    | 'greeting'
    | 'code_input'
    | 'code_verify'
    | 'name_input'
    | 'info_confirm'
    | 'pending_actions'
    | 'complete'
    | 'error'
    | 'human_escalation';
  /** Quick reply options for current state */
  quickReplies: string[];
  /** Actions to execute (e.g., complete_checkin) */
  actions: Array<{ type: string; [key: string]: unknown }>;
  /** Additional metadata from backend */
  metadata: Record<string, unknown>;
}

export interface UseCheckinConversationOptions {
  /** Clinic ID from QR code */
  clinicId: string;
  /** Optional clinic display name */
  clinicName?: string;
  /** Enable streaming responses for real-time UI updates */
  enableStreaming?: boolean;
  /** Called when check-in is completed */
  onComplete?: (result: { appointmentId: string; patientId: string }) => void;
  /** Called on error */
  onError?: (error: string) => void;
}

export interface UseCheckinConversationReturn {
  /** Chat messages */
  messages: FIMessage[];
  /** Current conversation state */
  conversationState: ConversationState | null;
  /** Loading state */
  loading: boolean;
  /** Is assistant "typing" */
  isTyping: boolean;
  /** Session ID */
  sessionId: string | null;
  /** Current streaming message content (when streaming is enabled) */
  streamingMessage: string;
  /** Start the conversation */
  startConversation: () => Promise<void>;
  /** Send a message */
  sendMessage: (message: string) => Promise<void>;
  /** Send a quick reply */
  sendQuickReply: (reply: string) => Promise<void>;
  /** End the conversation */
  endConversation: () => Promise<void>;
}

// =============================================================================
// API CLIENT - OpenAI Compatible
// =============================================================================

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';

interface OpenAIMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

interface ChatCompletionRequest {
  messages: OpenAIMessage[];
  model?: string;
  temperature?: number;
  persona?: string;
  session_id?: string;
  // AURITY extensions
  receptionist_config?: {
    clinic_id: string;
    clinic_name?: string;
    enable_quick_replies?: boolean;
  };
}

interface ChatCompletionChoice {
  index: number;
  message: OpenAIMessage;
  finish_reason: string;
}

interface ChatCompletionUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

interface ChatCompletionResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: ChatCompletionChoice[];
  usage: ChatCompletionUsage;
  // AURITY extensions
  persona: string;
  receptionist_state?: ConversationState;
}

interface ChatCompletionStreamChoice {
  index: number;
  delta: {
    role?: string;
    content?: string;
  };
  finish_reason: string | null;
}

interface ChatCompletionStreamResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: ChatCompletionStreamChoice[];
}

async function apiChatCompletion(
  request: ChatCompletionRequest
): Promise<ChatCompletionResponse> {
  const response = await fetch(`${API_BASE}/api/aurity/assistant/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Assistant chat failed: ${response.statusText}`);
  }

  return response.json();
}

async function* apiChatCompletionStreaming(
  request: ChatCompletionRequest,
  onThinking?: (thinking: string) => void
): AsyncGenerator<ChatCompletionStreamResponse> {
  // Add stream: true to request
  const streamRequest = { ...request, stream: true };

  const response = await fetch(`${API_BASE}/api/aurity/assistant/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(streamRequest),
  });

  if (!response.ok) {
    throw new Error(`Assistant streaming failed: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) {
    throw new Error('Response body is not readable');
  }

  try {
    let buffer = '';
    let lastEvent: string | null = null;

    while (true) {
      const { done, value } = await reader.read();

      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          lastEvent = line.slice(7).trim();
          continue;
        }
        if (line.startsWith('data: ')) {
          const data = line.slice(6); // Remove 'data: ' prefix

          if (data === '[DONE]') {
            return; // End of stream
          }

          try {
            if (lastEvent === 'meta') {
              const metaObj = JSON.parse(data) as { thinking?: string };
              if (metaObj.thinking && onThinking) {
                onThinking(metaObj.thinking);
              }
            } else {
              const chunk: ChatCompletionStreamResponse = JSON.parse(data);
              yield chunk;
            }
          } catch (error) {
            console.warn('Failed to parse SSE chunk:', data, error);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// =============================================================================
// HOOK
// =============================================================================

export function useCheckinConversation({
  clinicId,
  clinicName,
  enableStreaming = false,
  onComplete,
  onError,
}: UseCheckinConversationOptions): UseCheckinConversationReturn {
  const [messages, setMessages] = useState<FIMessage[]>([]);
  const [conversationState, setConversationState] =
    useState<ConversationState | null>(null);
  const [loading, setLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [streamingMessage, setStreamingMessage] = useState<string>(''); // Current streaming message content
  const [streamingThinking, setStreamingThinking] = useState<string>(''); // Optional reasoning received via SSE meta

  const messageIdCounter = useRef(0);

  const generateMessageId = useCallback(() => {
    messageIdCounter.current += 1;
    return `msg-${Date.now()}-${messageIdCounter.current}`;
  }, []);

  // Handle streaming response
  const handleStreamingResponse = useCallback(async (
    request: ChatCompletionRequest,
    onComplete: (response: ChatCompletionResponse) => void
  ) => {
    try {
      setStreamingMessage(''); // Reset streaming message
      setIsTyping(true);

      let fullContent = '';
      let finalResponse: ChatCompletionResponse | null = null;

      for await (const chunk of apiChatCompletionStreaming(request, setStreamingThinking)) {
        const choice = chunk.choices[0];
        if (choice.delta.content) {
          fullContent += choice.delta.content;
          setStreamingMessage(fullContent);
        }

        // Check if this is the final chunk
        if (choice.finish_reason === 'stop') {
          // Create final response object
          finalResponse = {
            id: chunk.id,
            object: 'chat.completion',
            created: chunk.created,
            model: chunk.model,
            choices: [{
              index: 0,
              message: { role: 'assistant', content: fullContent },
              finish_reason: 'stop'
            }],
            usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 }, // Placeholder
            persona: 'receptionist', // Will be updated by onComplete if needed
          };
          break;
        }
      }

      if (finalResponse) {
        onComplete(finalResponse);
      }
    } catch (error) {
      console.error('[useCheckinConversation] Streaming failed:', error);
      throw error;
    } finally {
      setIsTyping(false);
      setStreamingMessage('');
      setStreamingThinking('');
    }
  }, []);

  // Add message to state
  const addMessage = useCallback(
    (role: 'user' | 'assistant', content: string, thinking?: string | null) => {
      const newMessage: FIMessage = {
        role,
        content,
        timestamp: new Date().toISOString(),
        metadata: {
          id: generateMessageId(),
        },
        thinking: thinking ?? null,
      };
      setMessages((prev) => [...prev, newMessage]);
      return newMessage;
    },
    [generateMessageId]
  );

  // Start conversation
  const startConversation = useCallback(async () => {
    if (sessionId) return; // Already started

    setLoading(true);
    setIsTyping(true);

    try {
      // Generate unique session ID
      const newSessionId = `checkin-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      setSessionId(newSessionId);

      // Create initial system message for receptionist persona
      const systemMessage: OpenAIMessage = {
        role: 'system',
        content: `You are a friendly receptionist at ${clinicName || 'the clinic'}. Help patients check in conversationally. Be warm, efficient, and guide them through the check-in process. Keep responses concise and ask one question at a time.`
      };

      const initialMessage: OpenAIMessage = {
        role: 'user',
        content: 'Hello, I\'d like to check in for my appointment.'
      };

      const request: ChatCompletionRequest = {
        messages: [systemMessage, initialMessage],
        // model is determined by backend based on persona config
        temperature: 0.7,
        persona: 'receptionist',
        session_id: newSessionId,
        receptionist_config: {
          clinic_id: clinicId,
          clinic_name: clinicName,
          enable_quick_replies: true,
        },
      };

      let response: ChatCompletionResponse | null = null;

      if (enableStreaming) {
        // Use streaming API
        await handleStreamingResponse(request, (streamingResponse) => {
          response = streamingResponse;
        });
      } else {
        // Use regular API
        response = await apiChatCompletion(request);
      }

      if (!response) {
        throw new Error('Failed to get response from assistant API');
      }

      // Extract assistant response
      const assistantMessage = response.choices[0].message;
      addMessage('assistant', assistantMessage.content, streamingThinking || null);

      // Extract receptionist state from AURITY extensions
      if (response.receptionist_state) {
        setConversationState(response.receptionist_state);
      } else {
        // Fallback state if not provided
        setConversationState({
          state: 'greeting',
          quickReplies: ['I have an appointment', 'I\'m new here'],
          actions: [],
          metadata: { session_id: newSessionId },
        });
      }
    } catch (error) {
      console.error('[useCheckinConversation] Start failed:', error);
      onError?.(error instanceof Error ? error.message : 'Failed to start');
    } finally {
      setLoading(false);
      setIsTyping(false);
    }
  }, [clinicId, clinicName, sessionId, addMessage, onError, enableStreaming, handleStreamingResponse]);

  // Send message
  const sendMessage = useCallback(
    async (message: string) => {
      if (!sessionId || loading) return;

      // Add user message immediately
      addMessage('user', message);

      setLoading(true);
      setIsTyping(true);

      try {
        // Build conversation history in OpenAI format
        const conversationMessages: OpenAIMessage[] = [
          {
            role: 'system',
            content: `You are a friendly receptionist at ${clinicName || 'the clinic'}. Help patients check in conversationally. Be warm, efficient, and guide them through the check-in process. Keep responses concise and ask one question at a time.`
          },
          ...messages.map(m => ({
            role: m.role as 'user' | 'assistant',
            content: m.content,
          })),
          { role: 'user', content: message },
        ];

        const request: ChatCompletionRequest = {
          messages: conversationMessages,
          // model is determined by backend based on persona config
          temperature: 0.7,
          persona: 'receptionist',
          session_id: sessionId,
          receptionist_config: {
            clinic_id: clinicId,
            clinic_name: clinicName,
            enable_quick_replies: true,
          },
        };

        let response: ChatCompletionResponse | null = null;

        if (enableStreaming) {
          // Use streaming API
          await handleStreamingResponse(request, (streamingResponse) => {
            response = streamingResponse;
          });
        } else {
          // Use regular API
          response = await apiChatCompletion(request);
        }

        if (!response) {
          throw new Error('Failed to get response from assistant API');
        }

        // Extract assistant response
        const assistantMessage = response.choices[0].message;
        addMessage('assistant', assistantMessage.content, streamingThinking || null);

        // Update conversation state from AURITY extensions
        if (response.receptionist_state) {
          setConversationState(response.receptionist_state);

          // Check for completion
          if (response.receptionist_state.state === 'complete') {
            const completeAction = response.receptionist_state.actions?.find(
              (a) => a.type === 'complete_checkin'
            );
            if (completeAction && onComplete) {
              onComplete({
                appointmentId: completeAction.appointment_id as string,
                patientId: completeAction.patient_id as string,
              });
            }
          }
        }
      } catch (error) {
        console.error('[useCheckinConversation] Send failed:', error);
        addMessage(
          'assistant',
          'Lo siento, hubo un error. Por favor intente de nuevo o solicite ayuda en recepción.'
        );
        onError?.(error instanceof Error ? error.message : 'Failed to send');
      } finally {
        setLoading(false);
        setIsTyping(false);
      }
    },
    [sessionId, loading, messages, clinicId, clinicName, addMessage, onComplete, onError, enableStreaming, handleStreamingResponse]
  );

  // Send quick reply (same as sendMessage but for buttons)
  const sendQuickReply = useCallback(
    async (reply: string) => {
      await sendMessage(reply);
    },
    [sendMessage]
  );

  // End conversation
  const endConversation = useCallback(async () => {
    setSessionId(null);
    setConversationState(null);
    setMessages([]);
    setStreamingMessage('');
  }, []);

  return {
    messages,
    conversationState,
    loading,
    isTyping,
    sessionId,
    streamingMessage,
    startConversation,
    sendMessage,
    sendQuickReply,
    endConversation,
  };
}
