/**
 * Session types for dashboard components
 * Used by SessionsTable and related components
 */

export interface Session {
  id: string;
  status: 'active' | 'complete' | 'new' | 'error';
  interaction_count: number;
  created_at: string;
  last_active: string;
  startTime?: string;
  endTime?: string;
  patientName?: string;
  duration?: number;
  metadata?: Record<string, unknown>;
}
