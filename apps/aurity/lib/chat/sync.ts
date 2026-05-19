/**
 * Chat Sync Utilities
 *
 * Handles merging and deduplication of messages from localStorage and backend.
 * Ensures cross-device consistency while maintaining instant UX.
 */

import type { FIMessage } from '@aurity-standalone/types/assistant';

/**
 * Merge messages from localStorage and backend, removing duplicates.
 *
 * Strategy:
 * 1. Use timestamp + role + content as unique key
 * 2. Backend is source of truth (prefer backend in conflicts)
 * 3. Sort chronologically (oldest first)
 *
 * @param localMessages Messages from localStorage (instant cache)
 * @param backendMessages Messages from backend (source of truth)
 * @returns Merged and deduplicated messages
 */
export function mergeMessages(
  localMessages: FIMessage[],
  backendMessages: FIMessage[]
): FIMessage[] {
  // Deduplicate messages: prefer messages with IDs, use content as fallback
  const deduped: FIMessage[] = [];

  // Helper to check if message already exists
  const isDuplicate = (msg: FIMessage, existing: FIMessage[]): boolean => {
    return existing.some(e => {
      // Check 1: ID match (if both have IDs)
      if (msg.metadata?.id && e.metadata?.id) {
        return msg.metadata.id === e.metadata.id;
      }

      // Check 2: Timestamp match (within 5 seconds tolerance)
      const msgTime = new Date(msg.timestamp).getTime();
      const eTime = new Date(e.timestamp).getTime();
      const timeDiff = Math.abs(msgTime - eTime);

      if (timeDiff < 5000 && e.role === msg.role && e.content.trim() === msg.content.trim()) {
        return true;
      }

      // Check 3: Exact timestamp + role match (same message)
      if (msg.timestamp === e.timestamp && e.role === msg.role) {
        return true;
      }

      return false;
    });
  };

  // Add backend messages first (source of truth)
  backendMessages.forEach(msg => {
    if (!isDuplicate(msg, deduped)) {
      deduped.push(msg);
    }
  });

  // Add local messages (only if not in backend)
  let skippedCount = 0;
  localMessages.forEach(msg => {
    if (!isDuplicate(msg, deduped)) {
      deduped.push(msg);
    } else {
      skippedCount++;
    }
  });

  // Sort chronologically
  deduped.sort((a, b) => {
    const timeA = new Date(a.timestamp).getTime();
    const timeB = new Date(b.timestamp).getTime();
    return timeA - timeB;
  });

  // Merge stats tracked internally — no console output needed

  return deduped;
}

/**
 * Check if two message arrays are equivalent (for avoiding unnecessary updates)
 * Uses content-based comparison (ignores timestamp drift)
 */
export function areMessagesEqual(a: FIMessage[], b: FIMessage[]): boolean {
  if (a.length !== b.length) {
    return false;
  }

  return a.every((msg, idx) => {
    const other = b[idx];
    // Compare role + content only (timestamps can drift between client/server)
    return (
      msg.role === other.role &&
      msg.content.trim() === other.content.trim()
    );
  });
}
