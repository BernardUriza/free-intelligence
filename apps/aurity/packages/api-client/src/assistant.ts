/**
 * Assistant API Service
 *
 * Centralized API for AI assistant operations (chat, history search, etc.)
 * Replaces hardcoded fetch calls in HistorySearch component.
 *
 * Created: 2025-01-XX
 * Author: Claude Code (P1 Architectural Fix)
 */

import { api, getBackendUrl } from './client';
import { getRoles, type TokenClaims } from '@aurity-standalone/auth';
import { sanitizeMessagePreview, hash8 } from '@aurity-standalone/observability';

// ============================================================================
// Errors
// ============================================================================

export class BackendUnavailableError extends Error {
  constructor(message = 'Backend service is unavailable') {
    super(message);
    this.name = 'BackendUnavailableError';
  }
}

// ============================================================================
// Types
// ============================================================================

export interface HistorySearchRequest {
  query: string;
  doctor_id?: string;
  limit?: number;
}

export interface HistorySearchResponse {
  results: Array<{
    session_id: string;
    timestamp: string;
    query: string;
    response: string;
    relevance_score?: number;
  }>;
  total: number;
  total_interactions?: number; // Legacy field for backward compatibility
}

export interface ChatRequest {
  message: string;
  context?: Record<string, unknown>;
  conversationHistory?: Array<{ role: string; content: string }>;
  /** Doctor ID for H5 storage (Auth0 user.sub) */
  doctor_id?: string;
  /** Session ID for grouping messages */
  session_id?: string;
  /** Auth0 claims for RBAC validation (roles in https://aurity.app/roles) */
  claims?: TokenClaims;
  behavior_metrics?: {
    rapid_clicks?: number;
    repeated_messages?: number;
    idle_time_seconds?: number;
    back_navigations?: number;
    recent_errors?: number;
    phase_time_seconds?: number;
  };
  /** Enable model reasoning/thinking (Qwen3). Default true. Set false to skip thinking phase. */
  enable_thinking?: boolean;
  /** Response style: 'concise' for brief answers, 'explanatory' for detailed responses */
  response_mode?: string;
}

export interface ChatResponse {
  message: string;
  persona: string;
  voice?: string;
  emotional_analysis?: {
    state: string;
    confidence: number;
    suggested_tone: string;
    reason: string;
  };
  /** Model reasoning/thinking content (Qwen3 thinking mode) */
  thinking?: string;
}

// ============================================================================
// Assistant API
// ============================================================================

// ============================================================================
// Streaming Types
// ============================================================================

export interface StreamCallbacks {
  /** Called when thinking/reasoning content arrives */
  onThinking?: (thinking: string) => void;
  /** Called when content chunk arrives */
  onContent?: (content: string) => void;
  /** Called when stream completes */
  onComplete?: (response: ChatResponse & { thinking?: string }) => void;
  /** Called on error */
  onError?: (error: Error) => void;
  /** Called on abort */
  onAbort?: () => void;
}

export interface StreamController {
  /** Abort the stream */
  abort: () => void;
}

// ============================================================================
// Assistant API
// ============================================================================

export const assistantApi = {
  /**
   * Send a chat message to the assistant
   * Converts simplified request to OpenAI-compatible format and back
   */
  chat: async (request: ChatRequest): Promise<ChatResponse> => {
    // RBAC: only clinicians or superadmins can chat
    if (request.claims) {
      const roles = getRoles(request.claims);
      const allowed = roles.includes('FI-clinician') || roles.includes('FI-superadmin');
      if (!allowed) {
        throw new BackendUnavailableError('Acceso denegado: rol insuficiente');
      }
    }

    // Build OpenAI-compatible messages array
    const messages: Array<{ role: string; content: string }> = [];

    // Add conversation history if provided
    if (request.conversationHistory) {
      for (const msg of request.conversationHistory) {
        messages.push({
          role: msg.role,
          content: msg.content,
        });
      }
    }

    // Add the current user message
    messages.push({
      role: 'user',
      content: request.message,
    });

    // Call the OpenAI-compatible endpoint
    // Use 'user' field (OpenAI convention) for doctor_id
    // Telemetry-safe preview (no PHI)
    const preview = sanitizeMessagePreview(request.message, 60);
    const previewHash = hash8(preview);
    console.log('[assistantApi.chat]', {
      doctor_id_present: Boolean(request.doctor_id),
      session_id_present: Boolean(request.session_id),
      message_len: request.message.length,
      preview_hash8: previewHash,
    });
    const response = await api.post<{
      id: string;
      choices: Array<{
        message: { role: string; content: string };
        finish_reason: string;
      }>;
      persona: string;
      emotional_analysis?: ChatResponse['emotional_analysis'];
      thinking?: string | null;  // Qwen3 thinking mode
    }>('/api/workflows/aurity/assistant/chat', {
      messages,
      user: request.doctor_id, // OpenAI 'user' field = our doctor_id
      session_id: request.session_id,
      behavior_metrics: request.behavior_metrics,
      enable_thinking: request.enable_thinking ?? true, // Default true
      persona: (request.context?.persona as string) || 'general_assistant',
      response_mode: request.response_mode || (request.context?.response_mode as string) || 'explanatory',
    });

    // Extract the assistant's response
    const assistantMessage = response.choices?.[0]?.message?.content || '';
    const safeMsg = sanitizeMessagePreview(assistantMessage, 10_000);

    return {
      message: safeMsg,
      persona: response.persona || 'general_assistant',
      voice: 'nova', // Default voice
      emotional_analysis: response.emotional_analysis,
      thinking: response.thinking || undefined,  // Qwen3 thinking
    };
  },

  /**
   * Search conversation history
   */
  searchHistory: async (request: HistorySearchRequest): Promise<HistorySearchResponse> => {
    return api.post<HistorySearchResponse>(
      '/api/workflows/aurity/assistant/history/search',
      request
    );
  },

  /**
   * Get AI introduction message
   * Used for greeting users when starting a new conversation
   */
  introduction: async (context: Record<string, unknown>): Promise<ChatResponse> => {
    // Use the chat endpoint with a special introduction request
    const response = await api.post<{
      id: string;
      choices: Array<{
        message: { role: string; content: string };
        finish_reason: string;
      }>;
      persona: string;
    }>('/api/workflows/aurity/assistant/chat', {
      messages: [
        {
          role: 'system',
          content: 'Generate a brief, friendly greeting for a medical professional. Be concise and professional.',
        },
        {
          role: 'user',
          content: 'Hola',
        },
      ],
      user: context.doctor_id as string,
      persona: (context.persona as string) || 'general_assistant',
    });

    const assistantMessage = response.choices?.[0]?.message?.content || '¡Hola! ¿En qué puedo ayudarte hoy?';

    return {
      message: assistantMessage,
      persona: response.persona || 'general_assistant',
      voice: 'nova',
    };
  },

  /**
   * Stream a chat message from the assistant via SSE
   *
   * Best Practices 2025-2026:
   * - Real-time streaming with thinking/reasoning support
   * - Stop/abort capability
   * - Granular callbacks for UI updates
   *
   * @returns StreamController with abort() method
   */
  chatStream: (
    request: ChatRequest,
    callbacks: StreamCallbacks
  ): StreamController => {
    // RBAC: only clinicians or superadmins can stream
    if (request.claims) {
      const roles = getRoles(request.claims);
      const allowed = roles.includes('FI-clinician') || roles.includes('FI-superadmin');
      if (!allowed) {
        callbacks.onError?.(new BackendUnavailableError('Acceso denegado: rol insuficiente'));
        return { abort: () => void 0 };
      }
    }

    const { onThinking, onContent, onComplete, onError, onAbort } = callbacks;

    // Build OpenAI-compatible messages array
    const messages: Array<{ role: string; content: string }> = [];

    if (request.conversationHistory) {
      for (const msg of request.conversationHistory) {
        messages.push({ role: msg.role, content: msg.content });
      }
    }

    messages.push({ role: 'user', content: request.message });

    // Create abort controller
    const abortController = new AbortController();

    // Extract persona from request for use in onComplete
    const requestPersona = (request.context?.persona as string) || 'general_assistant';

    // Start streaming in background
    (async () => {
      let thinking = '';
      let content = '';
      let currentEvent = 'message';
      let responsePersona = requestPersona; // Default to request persona, may be updated by 'done' event

      try {
        const backendUrl = getBackendUrl();
        const response = await fetch(
          `${backendUrl}/api/workflows/aurity/assistant/chat/stream`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Accept: 'text/event-stream',
            },
            body: JSON.stringify({
              messages,
              user: request.doctor_id,
              session_id: request.session_id,
              behavior_metrics: request.behavior_metrics,
              enable_thinking: request.enable_thinking ?? true, // Default true
              stream: true, // Required for streaming endpoint
              persona: (request.context?.persona as string) || 'general_assistant',
              response_mode: request.response_mode || (request.context?.response_mode as string) || 'explanatory',
            }),
            signal: abortController.signal,
          }
        );

        if (!response.ok) {
          throw new Error(`Stream request failed: ${response.status}`);
        }

        if (!response.body) {
          throw new Error('Response body is null');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.trim()) continue;

            if (line.startsWith('event:')) {
              currentEvent = line.slice(6).trim();
              continue;
            }

            if (line.startsWith('data:')) {
              const data = line.slice(5).trim();
              if (data === '[DONE]') continue;

              try {
                const jsonData = JSON.parse(data);

                // Handle 'done' event with persona from backend
                if (jsonData.done === true && jsonData.persona) {
                  responsePersona = jsonData.persona;
                } else if (currentEvent === 'meta' && jsonData.thinking) {
                  thinking += jsonData.thinking;
                  onThinking?.(thinking);
                } else if (jsonData.choices?.[0]?.delta?.content) {
                  content += jsonData.choices[0].delta.content;
                  onContent?.(sanitizeMessagePreview(content, 10_000));
                }

                currentEvent = 'message';
              } catch {
                // Non-JSON data
                if (currentEvent === 'meta') {
                  thinking += data;
                  onThinking?.(sanitizeMessagePreview(thinking, 10_000));
                } else {
                  content += data;
                  onContent?.(sanitizeMessagePreview(content, 10_000));
                }
              }
            }
          }
        }

        // Stream complete - use persona from backend 'done' event (or fallback to request)
        onComplete?.({
          message: sanitizeMessagePreview(content, 10_000),
          persona: responsePersona,
          voice: 'nova',
          thinking: sanitizeMessagePreview(thinking, 10_000) || undefined,
        });
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
          onAbort?.();
          return;
        }
        onError?.(error instanceof Error ? error : new Error('Stream failed'));
      }
    })();

    return {
      abort: () => abortController.abort(),
    };
  },
};
