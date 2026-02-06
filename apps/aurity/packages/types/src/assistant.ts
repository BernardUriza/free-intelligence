/**
 * TypeScript Types for Free-Intelligence Assistant API
 *
 * Card: FI-ONBOARD-001
 * Free-Intelligence personality system with tone-based responses
 */

/**
 * FI Tone variants for contextual responses
 * - neutral: Standard informational tone
 * - empathetic: Supportive, understanding tone (for frustration/confusion)
 * - obsessive: Detail-oriented, thorough tone (for deep dives)
 * - sharp: Direct, incisive tone (for advanced users)
 */
export type FITone = 'neutral' | 'empathetic' | 'obsessive' | 'sharp';

/**
 * Onboarding phase context
 */
export type OnboardingPhase =
  | 'welcome'           // Phase 0: Meet FI
  | 'survey'            // Phase 1: Personalization
  | 'glitch'            // Phase 2: Glitch Elegante (error tolerance)
  | 'beta'              // Phase 3: Beta Permanente (continuous learning)
  | 'residencia'        // Phase 4: Residencia (sovereignty)
  | 'patient_setup'     // Phase 5: Patient Setup
  | 'first_consult'     // Phase 6: First Consultation
  | 'export'            // Phase 7: Export Evidence
  | 'complete';         // Phase 8: Pacto Sellado

/**
 * User role for personalization
 */
export type UserRole = 'medico_general' | 'especialista' | 'enfermera' | 'administrador';

/**
 * Clinic type for personalization
 */
export type ClinicType = 'privada' | 'publica' | 'mixta';

/**
 * AI experience level
 */
export type AIExperience = 'ninguna' | 'basica' | 'avanzada';

/**
 * Chat context passed to FI for personalization
 */
export interface FIChatContext {
  /** Current onboarding phase */
  phase?: OnboardingPhase;

  /** Doctor/User ID from JWT */
  doctor_id?: string;

  /** Doctor/User name */
  doctor_name?: string;

  /** Response mode preference */
  response_mode?: 'explanatory' | 'concise';

  /** Selected persona */
  persona?: string;

  /** User role (from survey) */
  userRole?: UserRole;

  /** Clinic type (from survey) */
  clinicType?: ClinicType;

  /** AI experience level (from survey) */
  aiExperience?: AIExperience;

  /** Consultas per day (from survey) */
  consultasPerDay?: '1-5' | '6-15' | '16-30' | '31+';

  /** Progress percentage (0-100) */
  progress?: number;

  /** Additional metadata (use sparingly, prefer explicit fields) */
  metadata?: Record<string, unknown>;
}

/**
 * Single message in FI conversation
 */
export interface FIMessage {
  /** Unique message ID */
  id?: string;

  /** Message role (user or assistant) */
  role: 'user' | 'assistant';

  /** Message content */
  content: string;

  /** Optional model reasoning (thinking) rendered before content */
  thinking?: string | null;

  /** ISO 8601 timestamp */
  timestamp: string;

  /** Optional metadata */
  metadata?: {
    /** FI tone used (assistant only) */
    tone?: FITone;

    /** Onboarding phase */
    phase?: OnboardingPhase;

    /** Message ID for tracking */
    id?: string;

    /** Azure TTS voice for this persona (assistant only) */
    voice?: string;

    /** LLM model that generated this message (e.g., "qwen3:1.7b", "claude-sonnet-4") */
    model?: string;

    /** Model reasoning/thinking content (2025-2026 best practice) */
    thinking?: string;
  };
}

/**
 * Behavior metrics for hybrid emotional analysis
 * Matches backend BehaviorMetrics schema
 */
export interface BehaviorMetrics {
  /** Number of rapid clicks (<500ms apart) */
  rapid_clicks: number;
  /** Number of repeated messages */
  repeated_messages: number;
  /** Seconds since last interaction */
  idle_time_seconds: number;
  /** Number of back navigations */
  back_navigations: number;
  /** Recent error count */
  recent_errors: number;
  /** Time on current phase in seconds */
  phase_time_seconds: number;
}

/**
 * LLM-analyzed emotional state from backend
 */
export interface EmotionalAnalysis {
  /** Detected emotional state */
  state: 'neutral' | 'frustrated' | 'successful' | 'hesitant';
  /** Confidence score 0-1 */
  confidence: number;
  /** Suggested tone for response */
  suggested_tone: 'neutral' | 'empathetic' | 'celebratory' | 'guiding';
  /** Reason for detection */
  reason: string;
}

/**
 * Request payload for /api/assistant/chat
 */
export interface FIChatRequest {
  /** User message */
  message: string;

  /** Context for personalization */
  context?: FIChatContext;

  /** Conversation history for continuity */
  conversationHistory?: FIMessage[];

  /** Behavior metrics for hybrid emotional analysis (optional) */
  behavior_metrics?: BehaviorMetrics;
}

/**
 * Response from /api/aurity/assistant/chat or /introduction
 * (Backend schema - adapted to match existing implementation)
 */
export interface FIChatResponse {
  /** FI response message */
  message: string;

  /** Persona used for response (e.g., "onboarding_guide", "general_assistant") */
  persona: string;

  /** Tokens consumed in this interaction */
  tokens_used: number;

  /** Response latency in milliseconds */
  latency_ms: number;

  /** Azure TTS voice for this persona (optional for backward compatibility) */
  voice?: string;

  /** LLM model that generated this response (e.g., "qwen3:1.7b", "claude-sonnet-4") */
  model?: string;

  /** LLM-analyzed emotional state (if behavior_metrics was sent) */
  emotional_analysis?: EmotionalAnalysis;

  /** Model reasoning/thinking content (Qwen3 thinking mode) */
  thinking?: string | null;
}

/**
 * Error response from Assistant API
 */
export interface FIErrorResponse {
  /** Error message */
  error: string;

  /** Error code */
  code?: string;

  /** HTTP status code */
  status?: number;

  /** Additional details */
  details?: any;
}

/**
 * Introduction request context
 */
export interface FIIntroductionContext {
  /** User's name (optional) */
  name?: string;

  /** User role (optional) */
  userRole?: UserRole;

  /** Any additional context */
  [key: string]: any;
}
