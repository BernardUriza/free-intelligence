/**
 * Timeline Resources Configuration
 * 
 * Defines the two resource rows for the timeline scheduler:
 * - Chat: User and assistant messages
 * - Audio: Transcriptions from audio sessions
 */

import type { BryntumResource } from '../types/scheduler.types';

/**
 * Timeline Resources
 * 
 * Categorized event sources matching backend TimelineEventType.
 * Groups events by functional area for better visualization.
 */
export const TIMELINE_RESOURCES: BryntumResource[] = [
  // User interactions
  {
    id: 'user',
    name: '👤 Usuario',
    eventColor: '#0ea5e9', // sky-500
  },
  
  // AI/Assistant responses
  {
    id: 'assistant',
    name: '🤖 Asistente',
    eventColor: '#8b5cf6', // violet-500
  },
  
  // Medical/Clinical actions
  {
    id: 'medical',
    name: '⚕️ Clínico',
    eventColor: '#06b6d4', // cyan-500
  },
  
  // System/Extraction processes
  {
    id: 'system',
    name: '⚙️ Sistema',
    eventColor: '#64748b', // slate-500
  },
  
  // Critical alerts
  {
    id: 'critical',
    name: '🚨 Crítico',
    eventColor: '#ef4444', // red-500
  },
  
  // Audio/Transcription
  {
    id: 'audio',
    name: '🎙️ Audio',
    eventColor: '#10b981', // emerald-500
  },
];

/**
 * Get resource by ID
 */
export function getResourceById(id: string): BryntumResource | undefined {
  return TIMELINE_RESOURCES.find((r) => r.id === id);
}

/**
 * Get resource name
 */
export function getResourceName(id: string): string {
  const resource = getResourceById(id);
  return resource?.name || 'Unknown';
}
