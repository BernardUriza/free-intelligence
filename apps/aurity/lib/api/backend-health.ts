/**
 * Backend Health Service - Passive Detection
 *
 * Singleton service that tracks backend availability using PASSIVE detection.
 * Does NOT make active health check requests (which would generate console errors).
 * Instead, it tracks failures from actual API calls and caches the "down" state.
 *
 * Design Pattern: Singleton + Observer + Circuit Breaker
 *
 * Usage:
 *   import { backendHealth } from '@aurity-standalone/api-client/backend-health';
 *
 *   // Check before making requests (returns true initially to allow first request)
 *   if (!backendHealth.shouldAttemptRequest()) {
 *     return fallbackBehavior();
 *   }
 *
 *   // Report failure after a request fails
 *   backendHealth.reportFailure();
 *
 *   // Report success after a request succeeds
 *   backendHealth.reportSuccess();
 *
 * File: apps/aurity/lib/api/backend-health.ts
 * Created: 2025-11-26
 */

// How long to wait before trying again after failures (circuit breaker)
const COOLDOWN_AFTER_FAILURE_MS = 60000; // 60 seconds
// How many failures before entering cooldown
const FAILURE_THRESHOLD = 2;

type HealthCallback = (available: boolean) => void;

class BackendHealthService {
  private static instance: BackendHealthService;
  private available: boolean = true; // Optimistic: assume available until proven otherwise
  private consecutiveFailures: number = 0;
  private lastFailureTime: number = 0;
  private subscribers: Set<HealthCallback> = new Set();

  private constructor() {
    // Private constructor for singleton
  }

  static getInstance(): BackendHealthService {
    if (!BackendHealthService.instance) {
      BackendHealthService.instance = new BackendHealthService();
    }
    return BackendHealthService.instance;
  }

  /**
   * Initialize (no-op for passive detection, kept for API compatibility)
   */
  async initialize(): Promise<boolean> {
    return this.available;
  }

  /**
   * Check if backend is available (for API compatibility)
   */
  isAvailable(): boolean {
    return this.shouldAttemptRequest();
  }

  /**
   * Should we attempt a request to the backend?
   * Returns true if:
   * - We haven't had enough failures to trigger cooldown
   * - OR the cooldown period has passed
   */
  shouldAttemptRequest(): boolean {
    // If we're in cooldown after failures, check if cooldown expired
    if (this.consecutiveFailures >= FAILURE_THRESHOLD) {
      const timeSinceLastFailure = Date.now() - this.lastFailureTime;
      if (timeSinceLastFailure < COOLDOWN_AFTER_FAILURE_MS) {
        // Still in cooldown - don't attempt
        return false;
      }
      // Cooldown expired - reset and allow one attempt
      console.log('[BackendHealth] Cooldown expired, allowing retry');
      this.consecutiveFailures = 0;
    }
    return true;
  }

  /**
   * Report a successful request - backend is available
   */
  reportSuccess(): void {
    const wasUnavailable = !this.available;
    this.available = true;
    this.consecutiveFailures = 0;
    this.lastFailureTime = 0;

    if (wasUnavailable) {
      console.log('[BackendHealth] Backend is now available');
      this.notifySubscribers();
    }
  }

  /**
   * Report a failed request - increment failure counter
   */
  reportFailure(): void {
    this.consecutiveFailures += 1;
    this.lastFailureTime = Date.now();

    // After threshold failures, mark as unavailable
    if (this.consecutiveFailures >= FAILURE_THRESHOLD && this.available) {
      this.available = false;
      console.log(`[BackendHealth] Backend unavailable after ${this.consecutiveFailures} failures (cooldown: ${COOLDOWN_AFTER_FAILURE_MS / 1000}s)`);
      this.notifySubscribers();
    }
  }

  /**
   * Force check (no-op for passive, kept for API compatibility)
   */
  async check(): Promise<boolean> {
    return this.available;
  }

  /**
   * Subscribe to health state changes
   */
  subscribe(callback: HealthCallback): () => void {
    this.subscribers.add(callback);

    // Immediately notify with current state
    callback(this.available);

    // Return unsubscribe function
    return () => {
      this.subscribers.delete(callback);
    };
  }

  /**
   * Notify all subscribers of state change
   */
  private notifySubscribers(): void {
    this.subscribers.forEach((callback) => {
      try {
        callback(this.available);
      } catch (err) {
        console.error('[BackendHealth] Subscriber error:', err);
      }
    });
  }

  /**
   * Cleanup (for testing)
   */
  destroy(): void {
    this.subscribers.clear();
    this.consecutiveFailures = 0;
    this.available = true;
  }
}

// Export singleton instance
export const backendHealth = BackendHealthService.getInstance();

// Export type for TypeScript
export type { BackendHealthService };
