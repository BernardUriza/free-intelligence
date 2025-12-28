/**
 * Audit Log Types
 * Card: FI-UI-FEAT-206
 *
 * Type definitions for audit log API responses.
 */

export interface AuditLogEntry {
  audit_id: string;
  timestamp: string;
  operation: string;
  user_id: string;
  endpoint: string;
  payload_hash: string;
  result_hash: string;
  status: "SUCCESS" | "FAILED" | "BLOCKED";
  metadata: string;
}

export interface AuditLogsResponse {
  total: number;
  limit: number;
  logs: AuditLogEntry[];
  operation_filter?: string;
  user_filter?: string;
}

export interface AuditStatsResponse {
  total_logs: number;
  exists: boolean;
  status_breakdown: Record<string, number>;
  operation_breakdown: Record<string, number>;
}

export interface AuditOperation {
  value: string;
  label: string;
  color: string;
}

export interface AuditOperationsResponse {
  operations: AuditOperation[];
}
