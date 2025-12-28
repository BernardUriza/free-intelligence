/**
 * Audit Log API Client
 * Card: FI-UI-FEAT-206
 */

import type {
  AuditLogsResponse,
  AuditStatsResponse,
  AuditOperationsResponse,
} from "../../types/audit";

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:7001";

export async function getAuditLogs(params?: {
  limit?: number;
  operation?: string;
  user?: string;
}): Promise<AuditLogsResponse> {
  const searchParams = new URLSearchParams();

  if (params?.limit) searchParams.append("limit", params.limit.toString());
  if (params?.operation) searchParams.append("operation", params.operation);
  if (params?.user) searchParams.append("user", params.user);

  const url = `${API_BASE}/api/audit/logs${searchParams.toString() ? `?${searchParams}` : ""}`;

  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch audit logs: ${response.statusText}`);
  }

  return response.json();
}

export async function getAuditStats(): Promise<AuditStatsResponse> {
  const response = await fetch(`${API_BASE}/api/audit/stats`, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch audit stats: ${response.statusText}`);
  }

  return response.json();
}

export async function getAuditOperations(): Promise<AuditOperationsResponse> {
  const response = await fetch(`${API_BASE}/api/audit/operations`, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch audit operations: ${response.statusText}`);
  }

  return response.json();
}
