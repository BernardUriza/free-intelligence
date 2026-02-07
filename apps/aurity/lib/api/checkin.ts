/**
 * Check-in API Client
 *
 * Card: FI-CHECKIN-001
 * HTTP client for patient self-service check-in system
 *
 * Updated: 2026-02 - Migrated to centralized api client
 */

import {
  Smartphone,
  Building2,
  PenLine,
  Lock,
  CreditCard,
  Coins,
  TestTube,
  FileX,
  ClipboardList,
  IdCard,
  FileText,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
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

import { api, getBackendUrl } from './client';

// =============================================================================
// API BASE
// =============================================================================

const API_BASE = '/api/checkin';

// =============================================================================
// CHECKIN API CLASS
// =============================================================================

export class CheckinAPI {
  // ---------------------------------------------------------------------------
  // QR CODE GENERATION
  // ---------------------------------------------------------------------------

  /**
   * Generate a QR code for check-in
   * Called by TV display to show scannable QR
   */
  async generateQR(clinicId: string): Promise<GenerateQRResponse> {
    return api.post<GenerateQRResponse>(`${API_BASE}/qr/generate`, { clinic_id: clinicId });
  }

  // ---------------------------------------------------------------------------
  // SESSION MANAGEMENT
  // ---------------------------------------------------------------------------

  /**
   * Start a new check-in session
   * Called when patient scans QR code
   */
  async startSession(
    clinicId: string,
    deviceType: 'mobile' | 'kiosk' | 'tablet' = 'mobile'
  ): Promise<CheckinSession> {
    return api.post<CheckinSession>(`${API_BASE}/session/start`, {
      clinic_id: clinicId,
      device_type: deviceType,
    });
  }

  /**
   * Get current session state
   */
  async getSession(sessionId: string): Promise<CheckinSession> {
    return api.get<CheckinSession>(`${API_BASE}/session/${sessionId}`);
  }

  // ---------------------------------------------------------------------------
  // PATIENT IDENTIFICATION
  // ---------------------------------------------------------------------------

  /**
   * Identify patient by 6-digit check-in code
   */
  async identifyByCode(request: IdentifyByCodeRequest): Promise<IdentifyPatientResponse> {
    return api.post<IdentifyPatientResponse>(`${API_BASE}/identify/code`, request);
  }

  /**
   * Identify patient by CURP
   */
  async identifyByCurp(request: IdentifyByCurpRequest): Promise<IdentifyPatientResponse> {
    return api.post<IdentifyPatientResponse>(`${API_BASE}/identify/curp`, request);
  }

  /**
   * Identify patient by name and date of birth
   */
  async identifyByName(request: IdentifyByNameRequest): Promise<IdentifyPatientResponse> {
    return api.post<IdentifyPatientResponse>(`${API_BASE}/identify/name`, request);
  }

  // ---------------------------------------------------------------------------
  // PENDING ACTIONS
  // ---------------------------------------------------------------------------

  /**
   * Get pending actions for an appointment
   */
  async getPendingActions(appointmentId: string): Promise<PendingAction[]> {
    const data = await api.get<{ actions: PendingAction[] }>(`${API_BASE}/actions/${appointmentId}`);
    return data.actions;
  }

  /**
   * Complete a pending action
   */
  async completeAction(
    actionId: string,
    data?: Record<string, unknown>
  ): Promise<PendingAction> {
    return api.post<PendingAction>(`${API_BASE}/actions/${actionId}/complete`, data || {});
  }

  /**
   * Skip a non-required pending action
   */
  async skipAction(actionId: string): Promise<PendingAction> {
    return api.post<PendingAction>(`${API_BASE}/actions/${actionId}/skip`);
  }

  // ---------------------------------------------------------------------------
  // COMPLETE CHECK-IN
  // ---------------------------------------------------------------------------

  /**
   * Complete the check-in process
   */
  async completeCheckin(request: CompleteCheckinRequest): Promise<CompleteCheckinResponse> {
    return api.post<CompleteCheckinResponse>(`${API_BASE}/complete`, request);
  }

  // ---------------------------------------------------------------------------
  // WAITING ROOM
  // ---------------------------------------------------------------------------

  /**
   * Get current waiting room state
   * Used by TV display to show queue
   */
  async getWaitingRoom(clinicId: string): Promise<WaitingRoomState> {
    const data = await api.get<GetWaitingRoomResponse>(`${API_BASE}/waiting-room/${clinicId}`);
    return data.state;
  }

  /**
   * Subscribe to waiting room updates (WebSocket)
   * Returns cleanup function
   *
   * Note: WebSocket connections require direct URL construction
   */
  subscribeToWaitingRoom(
    clinicId: string,
    onUpdate: (state: WaitingRoomState) => void
  ): () => void {
    const backendUrl = getBackendUrl();
    const wsUrl = backendUrl
      .replace('http://', 'ws://')
      .replace('https://', 'wss://');

    const ws = new WebSocket(`${wsUrl}${API_BASE}/waiting-room/${clinicId}/ws`);

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

    return () => {
      ws.close();
    };
  }

  // ---------------------------------------------------------------------------
  // DEPRECATED UTILITY
  // ---------------------------------------------------------------------------

  /** @deprecated Config is now handled automatically by api client */
  updateConfig(): void {
    console.warn('[CheckinAPI] updateConfig() is deprecated - config is handled automatically');
  }

  /** @deprecated Config is now handled automatically by api client */
  getConfig(): Record<string, unknown> {
    console.warn('[CheckinAPI] getConfig() is deprecated');
    return {};
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
 * Get action icon by type (returns Lucide icon component)
 */
export function getActionIcon(actionType: string): LucideIcon {
  const icons: Record<string, LucideIcon> = {
    update_contact: Smartphone,
    update_insurance: Building2,
    sign_consent: PenLine,
    sign_privacy: Lock,
    pay_copay: CreditCard,
    pay_balance: Coins,
    upload_labs: TestTube,
    upload_imaging: FileX,
    fill_questionnaire: ClipboardList,
    verify_identity: IdCard,
  };
  return icons[actionType] || FileText;
}
