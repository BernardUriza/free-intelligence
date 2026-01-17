/**
 * Timeline Event Transformation Utilities
 * 
 * Converts UnifiedEvent (from longitudinal memory API) to BryntumEvent format.
 * Handles color coding, resource assignment, and duration calculations.
 */

import type { UnifiedEvent, TransformedBryntumEvent } from '../types/scheduler.types';

/**
 * Event color mapping by type
 * Aligned with TIMELINE_COLORS from config
 */
export function getEventColor(eventType: string): string {
  switch (eventType) {
    case 'chat_user':
      return '#0ea5e9'; // sky-500
    case 'chat_assistant':
      return '#8b5cf6'; // violet-500
    case 'transcription':
      return '#10b981'; // emerald-500
    default:
      return '#64748b'; // slate-500
  }
}

/**
 * Resource assignment based on event type
 * Maps events to resource categories (user, assistant, medical, system, critical, audio)
 */
export function getResourceForEvent(event: UnifiedEvent): string {
  const eventType = event.event_type.toLowerCase();
  
  // User actions
  if (eventType.includes('user_message') || eventType.includes('user_upload') || eventType.includes('user_edit')) {
    return 'user';
  }
  
  // Assistant/AI responses
  if (eventType.includes('assistant') || eventType.includes('chat_assistant')) {
    return 'assistant';
  }
  
  // Medical/Clinical events
  if (eventType.includes('soap') || eventType.includes('diagnosis')) {
    return 'medical';
  }
  
  // Critical events
  if (eventType.includes('critical') || eventType.includes('urgency')) {
    return 'critical';
  }
  
  // Audio/Transcription
  if (eventType.includes('transcription') || event.source === 'audio') {
    return 'audio';
  }
  
  // System/Extraction (default)
  return 'system';
}

/**
 * Transform single event to Bryntum format
 */
export function transformEvent(event: UnifiedEvent): TransformedBryntumEvent {
  const startDate = new Date(event.timestamp * 1000);

  // Duration: use actual duration for audio, minimum 1 hour for visual display
  // Chat messages have no real duration, but need visual width to show content
  const MIN_DISPLAY_DURATION_SEC = 60 * 60; // 1 hour for text readability in day view
  const actualDuration = event.duration || 30; // 30s default for chat
  const displayDuration = Math.max(actualDuration, MIN_DISPLAY_DURATION_SEC);
  const durationMs = displayDuration * 1000;
  const endDate = new Date(startDate.getTime() + durationMs);

  // Truncate name for visual display
  const name = event.content.slice(0, 50) + (event.content.length > 50 ? '...' : '');

  return {
    id: event.id,
    resourceId: getResourceForEvent(event),
    startDate,
    endDate,
    name,
    eventColor: getEventColor(event.event_type),
    
    // Custom fields (preserved in event record)
    content: event.content,
    event_type: event.event_type,
    timestamp: event.timestamp,
    duration: event.duration ?? undefined,
    originalEvent: event,
  };
}

/**
 * Transform array of events to Bryntum format
 */
export function transformEvents(events: UnifiedEvent[]): TransformedBryntumEvent[] {
  return events.map(transformEvent);
}

/**
 * Get human-readable event type label (Spanish)
 */
export function getEventTypeLabel(eventType: string): string {
  switch (eventType) {
    case 'chat_user':
      return 'Usuario';
    case 'chat_assistant':
      return 'Asistente';
    case 'transcription':
      return 'Transcripción';
    default:
      return 'Desconocido';
  }
}
