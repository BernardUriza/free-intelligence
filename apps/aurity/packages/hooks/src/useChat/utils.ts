/**
 * useChat Utilities
 *
 * Helper functions for chat operations.
 * SOLID: Single Responsibility - pure utility functions.
 */

import type { BehaviorMetrics, FIMessage } from '@aurity-standalone/types/assistant';
import type { EmotionalMetrics } from '../useEmotionalContext';

/** Maximum messages to show initially */
export const INITIAL_MESSAGES_LIMIT = 3;

/**
 * Generate a unique message ID
 */
export function generateMessageId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Convert frontend EmotionalMetrics to backend BehaviorMetrics format
 */
export function metricsToBackendFormat(metrics: EmotionalMetrics | null): BehaviorMetrics | undefined {
  if (!metrics) return undefined;

  return {
    rapid_clicks: metrics.rapidClicks,
    repeated_messages: metrics.repeatedMessages,
    idle_time_seconds: Math.floor(metrics.idleTime / 1000),
    back_navigations: metrics.backNavigations,
    recent_errors: metrics.recentErrors,
    phase_time_seconds: Math.floor(metrics.phaseTime / 1000),
  };
}

/**
 * Check if an error is a connection error (expected when backend is down)
 */
export function isConnectionError(err: unknown): boolean {
  return (
    err instanceof TypeError &&
    (String(err).includes('fetch') || String(err).includes('NetworkError'))
  );
}

/**
 * Create message signature for deduplication
 * Uses role + first 100 chars of content as unique key
 */
export function getMessageSignature(msg: FIMessage): string {
  return `${msg.role}:${msg.content.trim().substring(0, 100)}`;
}

/**
 * Deduplicate messages by signature
 */
export function deduplicateMessages(
  existing: FIMessage[],
  incoming: FIMessage[]
): FIMessage[] {
  const existingSignatures = new Set(existing.map(getMessageSignature));
  return incoming.filter(m => !existingSignatures.has(getMessageSignature(m)));
}

/**
 * Check if message already exists (by ID or content)
 */
export function messageExists(
  messages: FIMessage[],
  newMessage: { role: string; content: string; metadata?: { id?: string } }
): boolean {
  return messages.some(m => {
    if (newMessage.metadata?.id && m.metadata?.id) {
      return m.metadata.id === newMessage.metadata.id;
    }
    return m.role === newMessage.role && m.content.trim() === newMessage.content.trim();
  });
}
