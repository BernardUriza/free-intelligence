/**
 * Audit Log API Client
 * Card: FI-UI-FEAT-206
 */

import type {
  AuditLogsResponse,
  AuditStatsResponse,
  AuditOperationsResponse,
} from "../../types/audit";
import { api } from "./client";

export async function getAuditLogs(params?: {
  limit?: number;
  operation?: string;
  user?: string;
}): Promise<AuditLogsResponse> {
  const searchParams = new URLSearchParams();

  if (params?.limit) searchParams.append("limit", params.limit.toString());
  if (params?.operation) searchParams.append("operation", params.operation);
  if (params?.user) searchParams.append("user", params.user);

  const query = searchParams.toString() ? `?${searchParams}` : "";
  return api.get<AuditLogsResponse>(`/api/audit/logs${query}`);
}

export async function getAuditStats(): Promise<AuditStatsResponse> {
  return api.get<AuditStatsResponse>("/api/audit/stats");
}

export async function getAuditOperations(): Promise<AuditOperationsResponse> {
  return api.get<AuditOperationsResponse>("/api/audit/operations");
}
