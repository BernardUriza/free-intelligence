/**
 * Message Storage Abstraction (Edge Architecture)
 *
 * PHILOSOPHY: Frontend ephemeral, Backend persistent
 * - Frontend: In-memory storage (session-scoped)
 * - Backend: HDF5 persistent storage (single source of truth)
 * - On reload: Backend sync restores messages
 *
 * This eliminates localStorage sync issues and aligns with edge architecture:
 * "Todo lo que esté en el Frontend debería estar cerca del Backend"
 *
 * Author: Bernard Uriza Orozco
 * Created: 2025-11-20
 * Updated: 2025-12-22 - Removed localStorage (will be Epic for proper implementation)
 * Card: FI-PHIL-DOC-014 (Memoria Longitudinal Unificada)
 */

import type { FIMessage } from '@aurity-standalone/types/assistant';

/**
 * Interface for message storage operations.
 *
 * Single Responsibility: ONLY handles message persistence.
 * Interface Segregation: Minimal interface, only what's needed.
 */
export interface IMessageStorage {
  /**
   * Load messages from storage.
   *
   * @param key Storage key (e.g., doctor_id)
   * @returns Array of messages, or empty array if none found
   */
  load(key: string): FIMessage[];

  /**
   * Save messages to storage.
   *
   * @param key Storage key
   * @param messages Messages to save
   */
  save(key: string, messages: FIMessage[]): void;

  /**
   * Clear messages from storage.
   *
   * @param key Storage key
   */
  clear(key: string): void;
}

/**
 * In-memory implementation (session-scoped storage).
 *
 * Messages live in memory during the session.
 * On page reload, backend sync restores messages via BackendSyncStrategy.
 *
 * Benefits:
 * - No localStorage sync conflicts
 * - Backend is single source of truth
 * - Aligns with edge architecture philosophy
 */
export class InMemoryMessageStorage implements IMessageStorage {
  private storage = new Map<string, FIMessage[]>();

  load(key: string): FIMessage[] {
    return this.storage.get(key) || [];
  }

  save(key: string, messages: FIMessage[]): void {
    this.storage.set(key, messages);
  }

  clear(key: string): void {
    this.storage.delete(key);
  }
}

/**
 * Factory: Create storage instance.
 *
 * Always returns InMemoryMessageStorage.
 * localStorage implementation removed to avoid sync issues.
 * Will be implemented as proper Epic with full sync strategy.
 */
export function createMessageStorage(_persistent: boolean): IMessageStorage {
  return new InMemoryMessageStorage();
}
