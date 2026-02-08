/**
 * Message Sync Strategies (SOLID: Strategy Pattern + Interface Segregation)
 *
 * Provides different strategies for synchronizing messages:
 * - BackendSyncStrategy: Periodic fetch from backend
 * - WebSocketSyncStrategy: Real-time updates via WebSocket
 *
 * Author: Bernard Uriza Orozco
 * Created: 2025-11-20
 * Card: FI-PHIL-DOC-014 (Memoria Longitudinal Unificada)
 */

import type { FIMessage, FITone, OnboardingPhase } from '@aurity-standalone/types/assistant';
import { backendHealth } from '@aurity-standalone/api-client/backend-health';
import { ROUTES } from '@/lib/api/routes';

function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('fi_access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Interface for backend sync operations.
 *
 * Single Responsibility: ONLY handles backend synchronization.
 * Interface Segregation: Minimal interface, focused on sync.
 */
export interface IBackendSync {
  /**
   * Fetch messages from backend and merge with local.
   *
   * @param doctorId Doctor identifier
   * @param phase Current onboarding phase
   * @param limit Max messages to fetch
   * @returns Merged messages
   */
  sync(
    doctorId: string,
    phase: OnboardingPhase | undefined,
    limit?: number
  ): Promise<FIMessage[]>;

  /**
   * Load older messages (for infinite scroll).
   *
   * @param doctorId Doctor identifier
   * @param phase Current onboarding phase
   * @param offset Pagination offset
   * @param limit Max messages to fetch
   * @returns Older messages + has_more flag
   */
  loadOlder(
    doctorId: string,
    phase: OnboardingPhase | undefined,
    offset: number,
    limit?: number
  ): Promise<{ messages: FIMessage[]; hasMore: boolean }>;
}

/**
 * Backend sync implementation.
 *
 * Single Responsibility: ONLY handles HTTP fetch + merge logic.
 * Open/Closed: Can extend with new backends without modifying.
 */
export class BackendSyncStrategy implements IBackendSync {
  private backendUrl: string;

  constructor(backendUrl?: string) {
    this.backendUrl = backendUrl || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';
  }

  async sync(
    doctorId: string,
    phase: OnboardingPhase | undefined,
    limit: number = 50
  ): Promise<FIMessage[]> {
    // Skip if circuit breaker is open
    if (!backendHealth.isAvailable()) {
      return [];
    }

    try {
      const response = await fetch(
        `${this.backendUrl}${ROUTES.assistantHistory}/paginated?` +
        `doctor_id=${encodeURIComponent(doctorId)}&` +
        `offset=0&` +
        `limit=${limit}`,
        { headers: getAuthHeaders() }
      );

      if (!response.ok) {
        // 404 = no history yet, 500 = doctor has no HDF5 file (e.g. superadmin)
        // Both are non-critical — return empty and let circuit breaker stay healthy
        if (response.status === 404 || response.status === 500) {
          return [];
        }
        throw new Error(`Backend sync failed: ${response.statusText}`);
      }

      const data = await response.json();

      // Convert backend interactions to FIMessage format
      const backendMessages: FIMessage[] = data.interactions.map((interaction: any) => {
        // Preserve persona from backend, only fallback for legacy messages without persona
        const persona = interaction.persona || 'general_assistant';
        if (!interaction.persona && interaction.role === 'assistant') {
          console.debug('[sync-strategy] Legacy message without persona, using fallback:', {
            timestamp: interaction.timestamp,
            preview: interaction.content?.slice(0, 50),
          });
        }
        return {
          role: interaction.role,
          content: interaction.content,
          timestamp: new Date(interaction.timestamp * 1000).toISOString(),
          metadata: {
            phase,
            tone: persona as FITone,
            model: interaction.model,  // LLM model from backend
          },
        };
      });

      backendHealth.reportSuccess();
      return backendMessages;
    } catch (err) {
      backendHealth.reportFailure();

      // Don't log connection errors (expected when backend is down)
      const isConnectionError = err instanceof TypeError && String(err).includes('fetch');
      if (!isConnectionError) {
        console.error('Backend sync failed (non-critical):', err);
      }
      return []; // Return empty array on failure (localStorage is still valid)
    }
  }

  async loadOlder(
    doctorId: string,
    phase: OnboardingPhase | undefined,
    offset: number,
    limit: number = 50
  ): Promise<{ messages: FIMessage[]; hasMore: boolean }> {
    try {
      const response = await fetch(
        `${this.backendUrl}${ROUTES.assistantHistory}/paginated?` +
        `doctor_id=${encodeURIComponent(doctorId)}&` +
        `offset=${offset}&` +
        `limit=${limit}`,
        { headers: getAuthHeaders() }
      );

      if (!response.ok) {
        throw new Error(`Failed to load older messages: ${response.statusText}`);
      }

      const data = await response.json();

      // Convert backend interactions to FIMessage format
      const olderMessages: FIMessage[] = data.interactions.map((interaction: any) => {
        const persona = interaction.persona || 'general_assistant';
        if (!interaction.persona && interaction.role === 'assistant') {
          console.debug('[sync-strategy] Legacy message without persona, using fallback:', {
            timestamp: interaction.timestamp,
            preview: interaction.content?.slice(0, 50),
          });
        }
        return {
          role: interaction.role,
          content: interaction.content,
          timestamp: new Date(interaction.timestamp * 1000).toISOString(),
          metadata: {
            phase,
            tone: persona as FITone,
            model: interaction.model,  // LLM model from backend
          },
        };
      });

      return {
        messages: olderMessages,
        hasMore: data.has_more,
      };
    } catch (err) {
      console.error('Failed to load older messages:', err);
      throw err;
    }
  }
}

/**
 * Interface for real-time sync (WebSocket).
 *
 * Single Responsibility: ONLY handles real-time updates.
 * Interface Segregation: Minimal interface for real-time operations.
 */
export interface IRealtimeSync {
  /**
   * Connect to real-time sync.
   *
   * @param doctorId Doctor identifier
   * @param onMessage Callback when new message received
   */
  connect(doctorId: string, onMessage: (message: FIMessage) => void): void;

  /**
   * Disconnect from real-time sync.
   */
  disconnect(): void;

  /**
   * Check if connected.
   */
  isConnected(): boolean;
}

/**
 * WebSocket sync implementation with Singleton pattern.
 *
 * Single Responsibility: ONLY handles WebSocket connection.
 * Open/Closed: Can extend with SSE, polling, etc. without modifying.
 * Singleton: Ensures only ONE WebSocket connection exists at a time.
 */
export class WebSocketSyncStrategy implements IRealtimeSync {
  private ws: WebSocket | null = null;
  private backendUrl: string;
  private reconnectAttempts = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private intentionalDisconnect = false; // Prevent reconnect on intentional close
  private currentDoctorId: string | null = null; // Track current connection
  private static MAX_LOG_ATTEMPTS = 3; // Only log first N reconnect attempts

  // Singleton: Global registry to prevent multiple instances
  private static activeInstance: WebSocketSyncStrategy | null = null;

  constructor(backendUrl?: string) {
    this.backendUrl = backendUrl || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';
  }

  connect(doctorId: string, onMessage: (message: FIMessage) => void): void {
    // Skip WebSocket connection if circuit breaker is open
    if (!backendHealth.isAvailable()) {
      return;
    }

    try {
      // SINGLETON PATTERN: Close previous instance if exists
      if (WebSocketSyncStrategy.activeInstance && WebSocketSyncStrategy.activeInstance !== this) {
        console.log('[WebSocket] Closing previous instance (hot-reload detected)');
        WebSocketSyncStrategy.activeInstance.disconnect();
      }

      // If already connected to same doctor, don't reconnect
      if (this.ws?.readyState === WebSocket.OPEN && this.currentDoctorId === doctorId) {
        console.log('[WebSocket] Already connected to same doctor, skipping');
        return;
      }

      // Register this instance as active
      WebSocketSyncStrategy.activeInstance = this;
      this.currentDoctorId = doctorId;

      // Reset intentional disconnect flag (new connection is intentional)
      this.intentionalDisconnect = false;

      // Close existing connection if any
      if (this.ws) {
        this.ws.close();
      }

      // Determine WebSocket URL (wss:// for production, ws:// for dev)
      const wsProtocol = this.backendUrl.startsWith('https') ? 'wss' : 'ws';
      const wsUrl = this.backendUrl.replace(/^https?/, wsProtocol);

      this.ws = new WebSocket(
        `${wsUrl}${ROUTES.assistant}/ws?doctor_id=${encodeURIComponent(doctorId)}`
      );

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected');
        this.reconnectAttempts = 0; // Reset reconnect attempts
        backendHealth.reportSuccess();
      };

      this.ws.onmessage = (event) => {
        try {
          // Handle ping/pong (plain text, not JSON)
          if (event.data === 'pong') {
            return; // Ignore pong responses
          }

          const data = JSON.parse(event.data);

          // Handle different message types
          if (data.type === 'new_message') {
            // Preserve persona from WebSocket, fallback for legacy only
            const persona = data.persona || 'general_assistant';
            if (!data.persona && data.role === 'assistant') {
              console.debug('[WebSocket] Message without persona, using fallback');
            }

            // Convert WebSocket message to FIMessage
            const message: FIMessage = {
              role: data.role as 'user' | 'assistant',
              content: data.content,
              timestamp: data.timestamp,
              metadata: {
                tone: persona as any,
                model: data.model,  // LLM model that generated this response
              },
            };

            onMessage(message);
          } else if (data.type === 'connected') {
            console.log('[WebSocket] Connection confirmed:', data);
          }
        } catch (err) {
          console.error('[WebSocket] Failed to parse message:', err);
        }
      };

      this.ws.onerror = () => {
        backendHealth.reportFailure();
        // Only log first error as warning to reduce console noise when backend is down
        if (this.reconnectAttempts === 0) {
          console.warn('[WebSocket] Backend unavailable (this is normal if backend is not running)');
        }
      };

      this.ws.onclose = () => {
        // Only log first disconnect as info
        if (this.reconnectAttempts === 0) {
          console.info('[WebSocket] Disconnected from backend');
        }

        // Only auto-reconnect if NOT an intentional disconnect
        if (this.intentionalDisconnect) {
          return;
        }

        // Don't reconnect if circuit breaker is open
        if (!backendHealth.isAvailable()) {
          return;
        }

        // Exponential backoff for reconnection
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
        this.reconnectAttempts += 1;

        this.reconnectTimeout = setTimeout(() => {
          this.connect(doctorId, onMessage);
        }, delay);
      };

      // Send ping every 30s to keep connection alive
      const pingInterval = setInterval(() => {
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send('ping');
        }
      }, 30000);

      // Store cleanup function
      (this.ws as any)._pingInterval = pingInterval;
    } catch (err) {
      console.error('[WebSocket] Connection failed:', err);
    }
  }

  disconnect(): void {
    // Set flag BEFORE closing to prevent auto-reconnect
    this.intentionalDisconnect = true;

    if (this.ws) {
      // Clear ping interval
      const pingInterval = (this.ws as any)._pingInterval;
      if (pingInterval) {
        clearInterval(pingInterval);
      }

      this.ws.close();
      this.ws = null;
    }

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    // Clear active instance if it's this one
    if (WebSocketSyncStrategy.activeInstance === this) {
      WebSocketSyncStrategy.activeInstance = null;
    }

    this.currentDoctorId = null;
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
