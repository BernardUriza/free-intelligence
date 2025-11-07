/**
 * Free Intelligence - Consultation Models
 *
 * Shared models for consultation state and SOAP notes.
 * Mirrors backend/fi_consult_models.py
 */

import { MessageRole, UrgencyLevel } from '../types/events';

export interface Message {
  role: MessageRole;
  content: string;
  timestamp: string; // ISO 8601
}

export interface Demographics {
  age?: number;
  gender?: string;
  occupation?: string;
  location?: string;
}

export interface Symptom {
  name: string;
  severity?: number; // 1-10
  duration?: string;
  location?: string;
}

export interface Comorbidity {
  condition: string;
  diagnosed_date?: string;
  treatment?: string;
}

export interface Medication {
  name: string;
  dosage?: string;
  frequency?: string;
}

export interface UrgencyAssessment {
  level: UrgencyLevel;
  reasoning: string;
  computed_at: string; // ISO 8601
  confidence?: number; // 0-1
}

export interface SOAPNote {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  generated_at: string; // ISO 8601
  version: number;
}

export interface CriticalPattern {
  pattern_name: string;
  confidence: number; // 0-1
  reasoning: string;
  detected_at: string; // ISO 8601
}

export interface ConsultationState {
  consultation_id: string;
  patient_id: string;
  user_id: string;
  started_at: string; // ISO 8601

  // Conversation
  messages: Message[];

  // Extracted data
  demographics?: Demographics;
  symptoms: Symptom[];
  comorbidities: Comorbidity[];
  medications: Medication[];

  // Assessment
  urgency_assessment?: UrgencyAssessment;
  critical_patterns: CriticalPattern[];

  // SOAP note
  soap_note?: SOAPNote;

  // Metadata
  extraction_iteration: number;
  extraction_progress: number; // 0-100
  committed: boolean;
  committed_at?: string; // ISO 8601
  audit_hash?: string;
}

/**
 * API Request/Response types
 */

export interface StartConsultationRequest {
  patient_id: string;
  user_id: string;
  metadata?: Record<string, unknown>;
}

export interface StartConsultationResponse {
  consultation_id: string;
  started_at: string;
}

export interface AppendEventRequest {
  event_type: string;
  data: Record<string, unknown>;
}

export interface AppendEventResponse {
  success: boolean;
  event_id: string;
  timestamp: string;
}

export interface GetConsultationResponse {
  consultation: ConsultationState;
}

export interface GetSOAPResponse {
  soap_note: SOAPNote;
  consultation_id: string;
}

export interface GetEventsResponse {
  consultation_id: string;
  events: Array<{
    event_type: string;
    timestamp: string;
    data: Record<string, unknown>;
  }>;
  total_events: number;
}
