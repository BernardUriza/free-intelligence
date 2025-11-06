/**
 * Shared API types for FI-Stride PWA
 * Prevents duplication and ensures type consistency across frontend
 */

// ============================================================================
// CONSULTATION TYPES
// ============================================================================

export interface ConsultationMetadata {
  id: string
  consultationId: string
  eventCount: number
  createdAt: string
  updatedAt?: string
}

export interface ConsultationsResponse {
  consultations: ConsultationMetadata[]
  total: number
  limit: number
  offset: number
}

// ============================================================================
// T21 RESOURCE TYPES
// ============================================================================

export type ResourceCategory = 'guide' | 'video' | 'article' | 'tool'

export interface T21Resource {
  id: string
  title: string
  description: string
  category: ResourceCategory
  icon: string
  url?: string
  tags?: string[]
}

export interface T21ResourcesResponse {
  resources: T21Resource[]
  total: number
  category?: string
}

// ============================================================================
// ERROR HANDLING
// ============================================================================

export interface ApiError {
  status: number
  message: string
  details?: Record<string, unknown>
}

export class ApiErrorClass extends Error implements ApiError {
  status: number
  message: string
  details?: Record<string, unknown>

  constructor(status: number, message: string, details?: Record<string, unknown>) {
    super(message)
    this.status = status
    this.message = message
    this.details = details
    this.name = 'ApiError'
  }
}

// ============================================================================
// PAGINATION
// ============================================================================

export interface PaginationParams {
  limit: number
  offset: number
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  limit: number
  offset: number
}

// ============================================================================
// SESSION & KATNISS TYPES
// ============================================================================

export interface SessionData {
  duration: number
  rpe: number
  emotionalCheckIn: 'happy' | 'neutral' | 'tired'
  notes: string
  athleteName?: string
}

export interface KATNISSResponse {
  motivation: string
  suggestion: string
  dayRecommended: string
  nextSteps: string[]
  sessionId?: string
}

// ============================================================================
// SUPPORT CONTACTS
// ============================================================================

export interface SupportContacts {
  hotline?: {
    name: string
    phone: string
    hours: string
  }
  email?: {
    address: string
    response_time: string
  }
  chat?: {
    available: string
    language: string
  }
}
