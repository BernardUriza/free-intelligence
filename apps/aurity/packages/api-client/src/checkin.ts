/**
 * Check-in API Client
 *
 * Card: FI-CHECKIN-001
 * HTTP client for patient self-service check-in system
 */

import type {
  CheckinSession,
  GenerateQRResponse,
  IdentifyByCodeRequest,
  IdentifyByCurpRequest,
  IdentifyByNameRequest,
  IdentifyPatientResponse,
  CompleteCheckinRequest,
  CompleteCheckinResponse,
  GetWaitingRoomResponse,
  WaitingRoomState,
  PendingAction,
} from '@aurity-standalone/types/checkin';

// =============================================================================
// API CONFIGURATION
// =============================================================================

interface CheckinAPIConfig {
  baseURL: string;
  timeout?: number;
  maxRetries?: number;
  retryDelay?: number;
}

const DEFAULT_CONFIG: Required<CheckinAPIConfig> = {
  baseURL: process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001',
  timeout: 10000,
  maxRetries: 2,
  retryDelay: 1000,
};

// =============================================================================
// FETCH WITH RETRY
// =============================================================================

async function fetchWithRetry(
  url: string,
  options: RequestInit,
  config: Required<CheckinAPIConfig>
): Promise<Response> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt < config.maxRetries; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), config.timeout);

      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok && response.status >= 400 && response.status < 500) {
        const error = await response.json();
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return response;
    } catch (error) {
      lastError = error as Error;

      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`Request timeout after ${config.timeout}ms`);
      }

      if (attempt === config.maxRetries - 1) {
        break;
      }

      const delay = config.retryDelay * Math.pow(2, attempt);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw lastError || new Error('Unknown error during fetch');
}

// =============================================================================
// CHECKIN API CLASS
// =============================================================================

export class CheckinAPI {
  private config: Required<CheckinAPIConfig>;

  constructor(config?: Partial<CheckinAPIConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  // ---------------------------------------------------------------------------
  // QR CODE GENERATION
  // ---------------------------------------------------------------------------

  /**
   * Generate a QR code for check-in
   * Called by TV display to show scannable QR
   *
   * @param clinicId The clinic ID to generate QR for
   * @returns QR code data (base64 image + URL)
   */
  async generateQR(clinicId: string): Promise<GenerateQRResponse> {
    const url = `${this.config.baseURL}/api/checkin/qr/generate`;

    const response = await fetchWithRetry(
      url,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clinic_id: clinicId }),
      },
      this.config
    );

    return response.json();
  }

  // ---------------------------------------------------------------------------
  // SESSION MANAGEMENT
  // ---------------------------------------------------------------------------

  /**
   * Start a new check-in session
   * Called when patient scans QR code
   *
   * @param clinicId The clinic ID from QR code
   * @param deviceType Device type (mobile, kiosk, tablet)
   * @returns New check-in session
   */
  async startSession(
    clinicId: string,
    deviceType: 'mobile' | 'kiosk' | 'tablet' = 'mobile'
  ): Promise<CheckinSession> {
    const url = `${this.config.baseURL}/api/checkin/session/start`;

    const response = await fetchWithRetry(
      url,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clinic_id: clinicId,
          device_type: deviceType,
        }),
      },
      this.config
    );

    return response.json();
  }

  /**
   * Get current session state
   *
   * @param sessionId The session ID
   * @returns Current session state
   */
  async getSession(sessionId: string): Promise<CheckinSession> {
    const url = `${this.config.baseURL}/api/checkin/session/${sessionId}`;

    const response = await fetchWithRetry(
      url,
      { method: 'GET' },
      this.config
    );

    return response.json();
  }

  // ---------------------------------------------------------------------------
  // PATIENT IDENTIFICATION
  // ---------------------------------------------------------------------------

  /**
   * Identify patient by 6-digit check-in code
   *
   * @param request Code identification request
   * @returns Patient and appointment info
   */
  async identifyByCode(request: IdentifyByCodeRequest): Promise<IdentifyPatientResponse> {
    const url = `${this.config.baseURL}/api/checkin/identify/code`;

    const response = await fetchWithRetry(
      url,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      },
      this.config
    );

    return response.json();
  }

  /**
   * Identify patient by CURP
   *
   * @param request CURP identification request
   * @returns Patient and appointment info
   */
  async identifyByCurp(request: IdentifyByCurpRequest): Promise<IdentifyPatientResponse> {
    const url = `${this.config.baseURL}/api/checkin/identify/curp`;

    const response = await fetchWithRetry(
      url,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      },
      this.config
    );

    return response.json();
  }

  /**
   * Identify patient by name and date of birth
   *
   * @param request Name/DOB identification request
   * @returns Patient and appointment info
   */
  async identifyByName(request: IdentifyByNameRequest): Promise<IdentifyPatientResponse> {
    const url = `${this.config.baseURL}/api/checkin/identify/name`;

    const response = await fetchWithRetry(
      url,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      },
      this.config
    );

    return response.json();
  }

  // ---------------------------------------------------------------------------
  // PENDING ACTIONS
  // ---------------------------------------------------------------------------

  /**
   * Get pending actions for an appointment
   *
   * @param appointmentId The appointment ID
   * @returns List of pending actions
   */
  async getPendingActions(appointmentId: string): Promise<PendingAction[]> {
    const url = `${this.config.baseURL}/api/checkin/actions/${appointmentId}`;

    const response = await fetchWithRetry(
      url,
      { method: 'GET' },
      this.config
    );

    const data = await response.json();
    return data.actions;
  }

  /**
   * Complete a pending action
   *
   * @param actionId The action ID
   * @param data Action-specific completion data
   * @returns Updated action
   */
  async completeAction(
    actionId: string,
    data?: Record<string, any>
  ): Promise<PendingAction> {
    const url = `${this.config.baseURL}/api/checkin/actions/${actionId}/complete`;

    const response = await fetchWithRetry(
      url,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data || {}),
      },
      this.config
    );

    return response.json();
  }

  /**
   * Skip a non-required pending action
   *
   * @param actionId The action ID
   * @returns Updated action
   */
  async skipAction(actionId: string): Promise<PendingAction> {
    const url = `${this.config.baseURL}/api/checkin/actions/${actionId}/skip`;

    const response = await fetchWithRetry(
      url,
      { method: 'POST' },
      this.config
    );

    return response.json();
  }

  // ---------------------------------------------------------------------------
  // COMPLETE CHECK-IN
  // ---------------------------------------------------------------------------

  /**
   * Complete the check-in process
   *
   * @param request Check-in completion request
   * @returns Check-in confirmation with queue position
   */
  async completeCheckin(request: CompleteCheckinRequest): Promise<CompleteCheckinResponse> {
    const url = `${this.config.baseURL}/api/checkin/complete`;

    const response = await fetchWithRetry(
      url,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      },
      this.config
    );

    return response.json();
  }

  // ---------------------------------------------------------------------------
  // WAITING ROOM
  // ---------------------------------------------------------------------------

  /**
   * Get current waiting room state
   * Used by TV display to show queue
   *
   * @param clinicId The clinic ID
   * @returns Waiting room state
   */
  async getWaitingRoom(clinicId: string): Promise<WaitingRoomState> {
    const url = `${this.config.baseURL}/api/checkin/waiting-room/${clinicId}`;

    const response = await fetchWithRetry(
      url,
      { method: 'GET' },
      this.config
    );

    const data: GetWaitingRoomResponse = await response.json();
    return data.state;
  }

  /**
   * Subscribe to waiting room updates (WebSocket)
   * Returns cleanup function
   *
   * @param clinicId The clinic ID
   * @param onUpdate Callback for state updates
   * @returns Cleanup function to close connection
   */
  subscribeToWaitingRoom(
    clinicId: string,
    onUpdate: (state: WaitingRoomState) => void
  ): () => void {
    const wsUrl = this.config.baseURL
      .replace('http://', 'ws://')
      .replace('https://', 'wss://');

    const ws = new WebSocket(`${wsUrl}/api/checkin/waiting-room/${clinicId}/ws`);

    ws.onmessage = (event) => {
      try {
        const state: WaitingRoomState = JSON.parse(event.data);
        onUpdate(state);
      } catch (error) {
        console.error('Failed to parse waiting room update:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    // Return cleanup function
    return () => {
      ws.close();
    };
  }

  // ---------------------------------------------------------------------------
  // UTILITY
  // ---------------------------------------------------------------------------

  updateConfig(config: Partial<CheckinAPIConfig>): void {
    this.config = { ...this.config, ...config };
  }

  getConfig(): Readonly<Required<CheckinAPIConfig>> {
    return { ...this.config };
  }
}

// =============================================================================
// SINGLETON INSTANCE
// =============================================================================

export const checkinAPI = new CheckinAPI();

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Format check-in code for display (XXX-XXX)
 */
export function formatCheckinCode(code: string): string {
  if (code.length !== 6) return code;
  return `${code.slice(0, 3)}-${code.slice(3)}`;
}

/**
 * Validate CURP format
 */
export function isValidCurp(curp: string): boolean {
  const curpRegex = /^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[A-Z0-9][0-9]$/;
  return curpRegex.test(curp.toUpperCase());
}

/**
 * Mask CURP for display (privacy)
 */
export function maskCurp(curp: string): string {
  if (curp.length !== 18) return curp;
  return `${curp.slice(0, 4)}${'*'.repeat(10)}${curp.slice(14)}`;
}

/**
 * Get estimated wait time string
 */
export function formatWaitTime(minutes: number): string {
  if (minutes < 5) return 'Menos de 5 minutos';
  if (minutes < 15) return '5-15 minutos';
  if (minutes < 30) return '15-30 minutos';
  if (minutes < 60) return '30-60 minutos';
  const hours = Math.floor(minutes / 60);
  return `Más de ${hours} hora${hours > 1 ? 's' : ''}`;
}

/**
 * Get action icon key by type
 * Returns a key that maps to a Lucide icon (see lib/icons/checkin-icons.ts)
 */
export function getActionIconKey(actionType: string): string {
  const iconKeys: Record<string, string> = {
    update_contact: 'smartphone',
    update_insurance: 'building2',
    sign_consent: 'penLine',
    sign_privacy: 'lock',
    pay_copay: 'creditCard',
    pay_balance: 'coins',
    upload_labs: 'testTube',
    upload_imaging: 'fileX',
    fill_questionnaire: 'clipboardList',
    verify_identity: 'idCard',
  };
  return iconKeys[actionType] || 'fileText';
}

/**
 * @deprecated Use getActionIconKey instead - returns icon keys for Lucide icons
 */
export function getActionIcon(actionType: string): string {
  return getActionIconKey(actionType);
}
