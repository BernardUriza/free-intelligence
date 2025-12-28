/**
 * ErrorDeduplicator - Intelligent Duplicate Suppression
 *
 * Suppresses identical errors within a 5-second window using idempotency keys.
 * Implements in-memory cache with LRU eviction and TTL-based cleanup.
 *
 * Idempotency Key Formula:
 * hash8(mensaje_normalizado + "::" + tipo_error + "::" + traza_normalizada + "::" + origen_componente)
 *
 * This ensures that:
 * - Same error message + type + stack + component = same key (deduplicated)
 * - Different stack traces = different keys (not deduplicated)
 * - Different messages = different keys (not deduplicated)
 *
 * @module lib/audio/ErrorDeduplicator
 */

import { hash8 } from '@/lib/internal/observability';
import type {
  ClassifiedError,
  DedupeEntry,
} from './types/audio-errors.types';

/**
 * Deduplication window in milliseconds
 * Errors with identical keys within this window are suppressed.
 * @default 5000 (5 seconds)
 */
const DEDUPE_WINDOW_MS = 5000;

/**
 * Cache TTL in milliseconds
 * Entries not seen within this window are eligible for cleanup.
 * @default 60000 (60 seconds)
 */
const DEDUPE_CACHE_TTL_MS = 60000;

/**
 * Maximum number of entries in dedupe cache
 * When exceeded, oldest entries (by last_seen) are evicted.
 * @default 100
 */
const MAX_DEDUPE_ENTRIES = 100;

/**
 * Intelligent error deduplication using idempotency keys
 */
export class ErrorDeduplicator {
  /**
   * In-memory cache of dedupe entries
   * Key: idempotency_key (hash8)
   * Value: DedupeEntry with statistics
   */
  private cache: Map<string, DedupeEntry> = new Map();

  /**
   * Calculate idempotency key from error
   *
   * Formula: hash8(
   *   normalized_message + "::" +
   *   error_type + "::" +
   *   normalized_trace + "::" +
   *   component_origin
   * )
   *
   * This ensures deterministic keys for identical errors.
   *
   * @returns 8-character hexadecimal hash
   */
  private calculateKey(error: ClassifiedError): string {
    const parts = [
      error.mensaje,
      error.tipo_error,
      error.traza_normalizada || '',
      error.origen_componente,
    ];

    return hash8(parts.join('::'));
  }

  /**
   * Check if error should be suppressed due to deduplication
   *
   * @returns true if duplicate within window (should suppress)
   * @returns false if first occurrence or window expired (should log)
   */
  shouldSuppress(error: ClassifiedError): boolean {
    const key = this.calculateKey(error);
    const now = Date.now();
    const entry = this.cache.get(key);

    // First occurrence - add to cache and allow logging
    if (!entry) {
      this.cache.set(key, {
        idempotency_key: key,
        first_seen: now,
        last_seen: now,
        count: 1,
        suppressed: 0,
      });

      // Cleanup stale entries
      this.evictOldEntries(now);

      return false; // Don't suppress - new error
    }

    // Check if within dedupe window
    const withinWindow = now - entry.last_seen < DEDUPE_WINDOW_MS;

    if (withinWindow) {
      // Within window - suppress and update stats
      entry.suppressed += 1;
      entry.last_seen = now;
      entry.count += 1;
      return true; // Suppress duplicate
    } else {
      // Window expired - allow retry and reset suppression counter
      entry.count += 1;
      entry.last_seen = now;
      entry.suppressed = 0; // Reset suppression counter for new window
      return false; // Don't suppress - window expired
    }
  }

  /**
   * Get deduplication statistics
   *
   * @returns Object with cache size and total suppressed count
   */
  getStats(): {
    total_keys: number;
    total_suppressed: number;
    cache_size_kb: number;
  } {
    let total_suppressed = 0;

    for (const entry of this.cache.values()) {
      total_suppressed += entry.suppressed;
    }

    // Rough estimate of cache size (each entry ~100 bytes)
    const cache_size_kb = (this.cache.size * 100) / 1024;

    return {
      total_keys: this.cache.size,
      total_suppressed,
      cache_size_kb,
    };
  }

  /**
   * Get a specific cache entry (for testing/debugging)
   *
   * @returns DedupeEntry if found, undefined otherwise
   */
  getEntry(key: string): DedupeEntry | undefined {
    return this.cache.get(key);
  }

  /**
   * Evict stale and overflow entries
   *
   * Two-phase eviction:
   * 1. Remove entries older than TTL (stale cleanup)
   * 2. Remove oldest entries if cache exceeds max size (LRU eviction)
   *
   * @private
   */
  private evictOldEntries(now: number): void {
    // Phase 1: Remove stale entries (TTL-based)
    const staleThreshold = now - DEDUPE_CACHE_TTL_MS;

    for (const [key, entry] of this.cache.entries()) {
      if (entry.last_seen < staleThreshold) {
        this.cache.delete(key);
      }
    }

    // Phase 2: LRU eviction if still over limit
    if (this.cache.size > MAX_DEDUPE_ENTRIES) {
      // Sort by last_seen (oldest first)
      const sorted = Array.from(this.cache.entries()).sort(
        (a, b) => a[1].last_seen - b[1].last_seen
      );

      // Remove oldest entries until under limit
      const toRemove = sorted.slice(0, this.cache.size - MAX_DEDUPE_ENTRIES);
      toRemove.forEach(([key]) => this.cache.delete(key));
    }
  }

  /**
   * Clear cache (for testing purposes)
   *
   * @internal
   */
  clear(): void {
    this.cache.clear();
  }

  /**
   * Get all cache entries (for debugging)
   *
   * @returns Array of all DedupeEntry objects
   * @internal
   */
  getAllEntries(): DedupeEntry[] {
    return Array.from(this.cache.values());
  }
}
