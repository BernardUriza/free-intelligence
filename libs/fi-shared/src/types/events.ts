/**
 * Free Intelligence - Shared Event Types
 *
 * Domain events that flow between FI backend and AURITY frontend.
 * These types mirror the Python Pydantic models in backend/fi_consult_models.py
 */

export enum MessageRole {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system',
}

export enum UrgencyLevel {
  UNKNOWN = 'UNKNOWN',
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL',
}

export enum ExtractionStatus {
  PENDING = 'PENDING',
  IN_PROGRESS = 'IN_PROGRESS',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
}

export enum SOAPSection {
  SUBJECTIVE = 'SUBJECTIVE',
  OBJECTIVE = 'OBJECTIVE',
  ASSESSMENT = 'ASSESSMENT',
  PLAN = 'PLAN',
}

/**
 * Base event interface
 */
export interface DomainEvent {
  event_type: string;
  timestamp: string; // ISO 8601
  consultation_id: string;
  metadata?: Record<string, unknown>;
}

/**
 * CONSULTATION_STARTED
 */
export interface ConsultationStartedEvent extends DomainEvent {
  event_type: 'CONSULTATION_STARTED';
  patient_id: string;
  user_id: string;
}

/**
 * MESSAGE_RECEIVED
 */
export interface MessageReceivedEvent extends DomainEvent {
  event_type: 'MESSAGE_RECEIVED';
  message: {
    role: MessageRole;
    content: string;
    timestamp: string;
  };
}

/**
 * EXTRACTION_STARTED
 */
export interface ExtractionStartedEvent extends DomainEvent {
  event_type: 'EXTRACTION_STARTED';
  iteration: number;
}

/**
 * EXTRACTION_COMPLETED
 */
export interface ExtractionCompletedEvent extends DomainEvent {
  event_type: 'EXTRACTION_COMPLETED';
  iteration: number;
  extracted_fields: string[];
}

/**
 * DEMOGRAPHICS_UPDATED
 */
export interface DemographicsUpdatedEvent extends DomainEvent {
  event_type: 'DEMOGRAPHICS_UPDATED';
  demographics: {
    age?: number;
    gender?: string;
    occupation?: string;
  };
}

/**
 * SYMPTOMS_UPDATED
 */
export interface SymptomsUpdatedEvent extends DomainEvent {
  event_type: 'SYMPTOMS_UPDATED';
  symptoms: Array<{
    name: string;
    severity?: number;
    duration?: string;
  }>;
}

/**
 * URGENCY_CLASSIFIED
 */
export interface UrgencyClassifiedEvent extends DomainEvent {
  event_type: 'URGENCY_CLASSIFIED';
  urgency_level: UrgencyLevel;
  reasoning?: string;
}

/**
 * SOAP_GENERATION_STARTED
 */
export interface SOAPGenerationStartedEvent extends DomainEvent {
  event_type: 'SOAP_GENERATION_STARTED';
}

/**
 * SOAP_SECTION_COMPLETED
 */
export interface SOAPSectionCompletedEvent extends DomainEvent {
  event_type: 'SOAP_SECTION_COMPLETED';
  section: SOAPSection;
  content: string;
}

/**
 * SOAP_GENERATION_COMPLETED
 */
export interface SOAPGenerationCompletedEvent extends DomainEvent {
  event_type: 'SOAP_GENERATION_COMPLETED';
  soap_note: {
    subjective: string;
    objective: string;
    assessment: string;
    plan: string;
  };
}

/**
 * CRITICAL_PATTERN_DETECTED
 */
export interface CriticalPatternDetectedEvent extends DomainEvent {
  event_type: 'CRITICAL_PATTERN_DETECTED';
  pattern_name: string;
  confidence: number;
  reasoning: string;
}

/**
 * CONSULTATION_COMMITTED
 */
export interface ConsultationCommittedEvent extends DomainEvent {
  event_type: 'CONSULTATION_COMMITTED';
  audit_hash: string;
}

/**
 * Union type of all events
 */
export type FIEvent =
  | ConsultationStartedEvent
  | MessageReceivedEvent
  | ExtractionStartedEvent
  | ExtractionCompletedEvent
  | DemographicsUpdatedEvent
  | SymptomsUpdatedEvent
  | UrgencyClassifiedEvent
  | SOAPGenerationStartedEvent
  | SOAPSectionCompletedEvent
  | SOAPGenerationCompletedEvent
  | CriticalPatternDetectedEvent
  | ConsultationCommittedEvent;
