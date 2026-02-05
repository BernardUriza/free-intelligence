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

/**
 * Error thrown when backend service is unavailable or unreachable
 * Use this for connection failures, timeouts, or 503 responses
 */
export class BackendUnavailableError extends Error {
  constructor(message = 'Backend service is unavailable') {
    super(message);
    this.name = 'BackendUnavailableError';
    // Maintain proper stack trace (V8 engines)
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, BackendUnavailableError);
    }
  }
}

/**
 * Error thrown when backend returns invalid/malformed response
 * Use this for unexpected response structure or missing required fields
 */
export class InvalidResponseError extends Error {
  constructor(message: string, public readonly context?: Record<string, unknown>) {
    super(message);
    this.name = 'InvalidResponseError';
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, InvalidResponseError);
    }
  }
}

// ============================================================================
// Types
// ============================================================================

/**
 * Request payload for searching conversation history
 */
export interface HistorySearchRequest {
  /** Search query text */
  query: string;
  /** Filter by doctor ID (Auth0 user.sub) */
  doctor_id?: string;
  /** Maximum number of results to return */
  limit?: number;
}

/**
 * Response from history search endpoint
 */
export interface HistorySearchResponse {
  /** Array of matching conversation results */
  results: Array<{
    /** Unique session identifier */
    session_id: string;
    /** ISO 8601 timestamp */
    timestamp: string;
    /** User query text */
    query: string;
    /** Assistant response text */
    response: string;
    /** Relevance score (0-1) */
    relevance_score?: number;
  }>;
  /** Total number of results found */
  total: number;
  /** @deprecated Legacy field for backward compatibility */
  total_interactions?: number;
}

/**
 * Request payload for chat endpoint
 * Follows OpenAI ChatCompletion format internally
 */
export interface ChatRequest {
  /** User message to send to assistant */
  message: string;
  /** Additional context for personalization */
  context?: Record<string, unknown>;
  /** Previous conversation messages for context */
  conversationHistory?: Array<{ role: string; content: string }>;
  /** Doctor ID for H5 storage (Auth0 user.sub) */
  doctor_id?: string;
  /** Session ID for grouping messages */
  session_id?: string;
  /** Auth0 claims for RBAC validation (roles in https://aurity.app/roles) */
  claims?: TokenClaims;
  /** Behavior metrics for hybrid emotional analysis */
  behavior_metrics?: {
    /** Number of rapid clicks (<500ms apart) */
    rapid_clicks?: number;
    /** Number of repeated identical messages */
    repeated_messages?: number;
    /** Seconds since last interaction */
    idle_time_seconds?: number;
    /** Number of back button navigations */
    back_navigations?: number;
    /** Recent error count */
    recent_errors?: number;
    /** Time spent in current phase (seconds) */
    phase_time_seconds?: number;
  };
  /** Enable model reasoning/thinking (Qwen3). Default true. Set false to save compute. */
  enable_thinking?: boolean;
  /** Response style: 'concise' (3-4 sentences) or 'explanatory' (detailed). Default 'explanatory'. */
  response_mode?: 'concise' | 'explanatory';
}

/**
 * Response from chat endpoint
 * Simplified from OpenAI ChatCompletionResponse format
 */
export interface ChatResponse {
  /** Assistant response message */
  message: string;
  /** Persona used for this response (e.g., "general_assistant") */
  persona: string;
  /** Azure TTS voice (e.g., "nova") */
  voice?: string;
  /** LLM model that generated this response (e.g., "qwen3:1.7b", "claude-sonnet-4") */
  model?: string;
  /** LLM-analyzed emotional state (when behavior_metrics provided) */
  emotional_analysis?: {
    /** Detected emotional state */
    state: string;
    /** Confidence score (0-1) */
    confidence: number;
    /** Suggested tone for next response */
    suggested_tone: string;
    /** Explanation for detection */
    reason: string;
  };
  /** Model reasoning/thinking content (Qwen3 thinking mode) */
  thinking?: string;
}

// ============================================================================
// Constants
// ============================================================================

/**
 * Timeout for LLM chat requests (2 minutes)
 * LLM inference can be slow, especially for local models like Qwen3
 */
const CHAT_TIMEOUT_MS = 120000; // 2 minutes

/**
 * Timeout for introduction requests (shorter since it's a simple greeting)
 */
const INTRO_TIMEOUT_MS = 60000; // 60 seconds (local Ollama can take 30-50s)

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Validates chat response structure
 * Throws InvalidResponseError if response is malformed
 */
function validateChatResponse(response: unknown): asserts response is {
  id: string;
  model: string;
  choices: Array<{
    message: { role: string; content: string };
    finish_reason: string;
  }>;
  persona: string;
  emotional_analysis?: ChatResponse['emotional_analysis'];
  thinking?: string | null;
} {
  if (!response || typeof response !== 'object') {
    throw new InvalidResponseError('Response is not an object', { response });
  }

  const r = response as Record<string, unknown>;

  if (!Array.isArray(r.choices) || r.choices.length === 0) {
    throw new InvalidResponseError('Response missing choices array', { response });
  }

  const firstChoice = r.choices[0] as Record<string, unknown>;
  if (!firstChoice.message || typeof firstChoice.message !== 'object') {
    throw new InvalidResponseError('Response missing message in first choice', { response });
  }
}

/**
 * Extracts assistant message from OpenAI-compatible response
 * Returns empty string if message is missing (defensive programming)
 */
function extractAssistantMessage(response: {
  choices: Array<{ message?: { content?: string } }>;
}): string {
  const content = response.choices?.[0]?.message?.content;
  if (typeof content !== 'string') {
    console.warn('[assistantApi] Missing or invalid message content', { response });
    return '';
  }
  return content;
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
    // Normalize persona: accept either string id or an object { id, name }
    let personaFromContext = 'general_assistant';
    const rawPersona = request.context?.persona;
    if (typeof rawPersona === 'string' && rawPersona.trim()) {
      personaFromContext = rawPersona;
    } else if (rawPersona && typeof rawPersona === 'object') {
      // If frontend passed a persona object, try to extract `id` or `value`
      // Defensive: avoid sending whole objects to backend
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      const maybeId = rawPersona.id || rawPersona.value || rawPersona.name;
      if (typeof maybeId === 'string' && maybeId.trim()) personaFromContext = maybeId;
    }
    console.log('[assistantApi.chat]', {
      doctor_id_present: Boolean(request.doctor_id),
      session_id_present: Boolean(request.session_id),
      message_len: request.message.length,
      preview_hash8: previewHash,
      persona: personaFromContext, // DEBUG: Log persona being sent
      context_keys: Object.keys(request.context || {}), // DEBUG: Log context structure
    });
    const payload = {
      messages,
      user: request.doctor_id, // OpenAI 'user' field = our doctor_id
      session_id: request.session_id,
      behavior_metrics: request.behavior_metrics,
      enable_thinking: request.enable_thinking ?? true, // Default true
      response_mode: request.response_mode ?? 'explanatory', // Default explanatory
      persona: personaFromContext, // Extract persona from context
    };

    console.log('[assistantApi.chat] Payload being sent:', {
      ...payload,
      messages: `[${payload.messages.length} messages]`, // Don't log full messages
    });

    // Add onboarding mode header for onboarding_guide persona (bypasses auth)
    const customHeaders: Record<string, string> = {};
    if (personaFromContext === 'onboarding_guide') {
      customHeaders['X-Onboarding-Mode'] = 'true';
    }

    const response = await api.post<{
      id: string;
      model: string;  // LLM model identifier
      choices: Array<{
        message: { role: string; content: string };
        finish_reason: string;
      }>;
      persona: string;
      emotional_analysis?: ChatResponse['emotional_analysis'];
      thinking?: string | null;  // Qwen3 thinking mode
    }>(
      '/api/aurity/assistant/chat',
      payload,
      {
        timeout: CHAT_TIMEOUT_MS, // 2 minutes for LLM inference
        customHeaders, // X-Onboarding-Mode for unauthenticated onboarding
      }
    );

    // Validate response structure
    validateChatResponse(response);

    // Extract and sanitize assistant's response
    const assistantMessage = extractAssistantMessage(response);
    const safeMsg = sanitizeMessagePreview(assistantMessage, 10_000);

    // DEBUG: Log backend response model
    console.log('[assistantApi.chat] Backend response:', {
      model: response.model,
      hasModel: Boolean(response.model),
      persona: response.persona,
    });

    // Return structured response with defaults
    return {
      message: safeMsg,
      persona: response.persona || 'general_assistant',
      voice: 'nova', // Default voice
      model: response.model || 'unknown',  // LLM model that generated this response
      emotional_analysis: response.emotional_analysis,
      thinking: response.thinking || undefined,  // Qwen3 thinking
    };
  },

  /**
   * Search conversation history
   */
  searchHistory: async (request: HistorySearchRequest): Promise<HistorySearchResponse> => {
    return api.post<HistorySearchResponse>(
      '/api/aurity/assistant/history/search',
      request
    );
  },

  /**
   * Get AI introduction message
   * Used for greeting users when starting a new conversation
   */
  introduction: async (
    context: Record<string, unknown>,
    signal?: AbortSignal
  ): Promise<ChatResponse> => {
    // Use dedicated introduction endpoint
    // Always include X-Onboarding-Mode for introduction (it's always during onboarding)
    const response = await api.post<{
      message: string;
      persona: string;
      tokens_used: number;
      latency_ms: number;
    }>(
      '/api/aurity/assistant/introduction',
      {
        physician_name: context.physician_name as string | undefined,
        clinic_name: context.clinic_name as string | undefined,
      },
      {
        timeout: INTRO_TIMEOUT_MS, // 60 seconds (local Ollama can take 30-50s)
        signal,
        customHeaders: { 'X-Onboarding-Mode': 'true' },
      }
    );

    return {
      message: response.message,
      persona: response.persona,
      voice: 'nova',
      model: 'qwen3:1.7b',  // Introduction uses default model
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

    // Start streaming in background
    (async () => {
      let thinking = '';
      let content = '';
      let model = '';
      let persona = '';  // Capture persona from backend done event
      let currentEvent = 'message';

      try {
        const backendUrl = getBackendUrl();
        const requestBody: Record<string, unknown> = {
          messages,
          user: request.doctor_id,
          session_id: request.session_id,
          behavior_metrics: request.behavior_metrics,
          enable_thinking: request.enable_thinking ?? true, // Default true
          stream: true, // Required for streaming endpoint
          // Extract persona from context (required by backend)
          persona: (request.context?.persona as string) || 'assistant',
        };

        // Include optional context fields if available
        if (request.context?.model) {
          requestBody.model = request.context.model;
        }
        if (request.context?.response_mode) {
          requestBody.response_mode = request.context.response_mode;
        }

        // Add onboarding mode header for onboarding_guide persona (bypasses auth)
        const streamHeaders: Record<string, string> = {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        };
        if (requestBody.persona === 'onboarding_guide') {
          streamHeaders['X-Onboarding-Mode'] = 'true';
        }

        console.log('[assistantApi.chatStream] [REQUEST] Sending request to backend:', {
          url: `${backendUrl}/api/aurity/assistant/chat/stream`,
          persona: requestBody.persona,
          messages: messages.length,
          lastMessage: messages[messages.length - 1]?.content?.substring(0, 50),
          hasOnboardingHeader: requestBody.persona === 'onboarding_guide',
        });

        const response = await fetch(
          `${backendUrl}/api/aurity/assistant/chat/stream`,
          {
            method: 'POST',
            headers: streamHeaders,
            body: JSON.stringify(requestBody),
            signal: abortController.signal,
          }
        );

        if (!response.ok) {
          console.error('[assistantApi.chatStream] [ERROR] Response not OK:', {
            status: response.status,
            statusText: response.statusText,
          });
          throw new Error(`Stream request failed: ${response.status}`);
        }

        if (!response.body) {
          throw new Error('Response body is null');
        }

        console.log('[assistantApi.chatStream] [OK] Response OK, starting to read stream...');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let chunkCount = 0;
        let dataLineCount = 0;

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            console.log('[assistantApi.chatStream] [DONE] Stream reading done');
            break;
          }

          chunkCount++;
          const decodedValue = decoder.decode(value, { stream: true });
          buffer += decodedValue;
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.trim()) continue;

            // DEBUG: Log every non-empty line received
            console.log('[assistantApi.chatStream] [RAW] RAW LINE:', line.substring(0, 80));

            if (line.startsWith('event:')) {
              currentEvent = line.slice(6).trim();
              console.log('[assistantApi.chatStream] [EVENT] Event type SET TO:', currentEvent);
              continue;
            }

            if (line.startsWith('data:')) {
              console.log('[assistantApi.chatStream] [DATA] Processing data line, currentEvent=', currentEvent);
              dataLineCount++;
              const data = line.slice(5).trim();
              if (data === '[DONE]') {
                console.log('[assistantApi.chatStream] [COMPLETE] Received [DONE]');
                continue;
              }

              try {
                const jsonData = JSON.parse(data);

                // Capture model and persona if present (sent by backend in done event)
                if (jsonData.model) {
                  model = jsonData.model;
                  console.log('[assistantApi.chatStream] [MODEL] Model:', model);
                }
                if (jsonData.persona) {
                  persona = jsonData.persona;
                  console.log('[assistantApi.chatStream] [PERSONA] Persona:', persona);
                }

                if (currentEvent === 'meta' && jsonData.thinking) {
                  thinking += jsonData.thinking;
                  console.log('[assistantApi.chatStream] [THINK] Thinking chunk:', jsonData.thinking.substring(0, 30) + '...');
                  onThinking?.(thinking);
                } else if (jsonData.choices?.[0]?.delta?.content) {
                  const deltaContent = jsonData.choices[0].delta.content;
                  content += deltaContent;
                  console.log('[assistantApi.chatStream] [CONTENT] Content delta:', deltaContent, '| Total length:', content.length);
                  // Call onContent immediately, then yield to ensure React commits this update
                  // before processing the next chunk (prevents React 18+ batching)
                  onContent?.(sanitizeMessagePreview(content, 10_000));
                  await new Promise(resolve => setTimeout(resolve, 0));  // Force new macrotask
                }

                currentEvent = 'message';
              } catch {
                console.warn('[assistantApi.chatStream] [WARN] Failed to parse JSON:', data.substring(0, 50));
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

        console.log('[assistantApi.chatStream] [STATS] Stream complete:', {
          totalChunks: chunkCount,
          dataLines: dataLineCount,
          contentLength: content.length,
          thinkingLength: thinking.length,
        });

        // Stream complete - use persona from backend or fallback to request persona
        onComplete?.({
          message: sanitizeMessagePreview(content, 10_000),
          persona: persona || (request.context?.persona as string) || 'general_assistant',
          voice: 'nova',
          model: model || undefined,  // LLM model that generated this response
          thinking: sanitizeMessagePreview(thinking, 10_000) || undefined,
        });
      } catch (error) {
        console.error('[assistantApi.chatStream] [FATAL] Stream error:', error);
        if (error instanceof Error && error.name === 'AbortError') {
          console.log('[assistantApi.chatStream] [ABORT] Stream aborted');
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
