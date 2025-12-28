/**
 * Audit Table Component
 * Card: FI-UI-FEAT-206
 */

import type { AuditLogEntry } from "../types/audit";

interface AuditTableProps {
  logs: AuditLogEntry[];
  onSelectLog: (log: AuditLogEntry) => void;
  selectedLog: AuditLogEntry | null;
}

const getOperationBadgeColor = (operation: string): string => {
  const colorMap: Record<string, string> = {
    LOGIN: "bg-green-900/30 fi-text-green border-green-700",
    POLICY_CHANGE: "bg-yellow-900/30 text-yellow-400 border-yellow-700",
    VERIFY: "bg-blue-900/30 fi-text-primary border-blue-700",
    EXPORT: "bg-purple-900/30 fi-text-purple border-purple-700",
    DELETE: "bg-red-900/30 fi-text-error border-red-700",
    INTERACTION_APPENDED: "bg-slate-700/30 text-slate-400 border-slate-600",
    SESSION_CREATED: "bg-slate-700/30 text-slate-400 border-slate-600",
  };

  return colorMap[operation] || "bg-slate-700/30 text-slate-400 border-slate-600";
};

const getStatusBadgeColor = (status: string): string => {
  switch (status) {
    case "SUCCESS":
      return "bg-green-900/30 fi-text-green";
    case "FAILED":
      return "bg-red-900/30 fi-text-error";
    case "BLOCKED":
      return "bg-yellow-900/30 text-yellow-400";
    default:
      return "bg-slate-700/30 text-slate-400";
  }
};

const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
};

const formatTime = (timestamp: string): string => {
  const date = new Date(timestamp);
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  const seconds = date.getSeconds().toString().padStart(2, '0');
  return `${hours}:${minutes}:${seconds}`;
};

const extractSessionId = (metadata: string): string | null => {
  try {
    const parsed = JSON.parse(metadata);
    return parsed.session_id || null;
  } catch {
    return null;
  }
};

export function AuditTable({ logs, onSelectLog, selectedLog }: AuditTableProps) {
  return (
    <div className="bg-slate-800 rounded-lg overflow-hidden">
      {/* Desktop View */}
      <div className="hidden lg:block overflow-x-auto">
        <table className="w-full">
          <thead className="bg-slate-700">
            <tr>
              <th className="fi-table-header">
                Timestamp
              </th>
              <th className="fi-table-header">
                Operation
              </th>
              <th className="fi-table-header">
                User
              </th>
              <th className="fi-table-header">
                Status
              </th>
              <th className="fi-table-header">
                Details
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {logs.map((log) => {
              const sessionId = extractSessionId(log.metadata);
              const isSelected = selectedLog?.audit_id === log.audit_id;

              return (
                <tr
                  key={log.audit_id}
                  className={`hover:bg-slate-700/50 fi-interactive ${
                    isSelected ? "bg-slate-700/70" : ""
                  }`}
                  onClick={() => onSelectLog(log)}
                >
                  <td className="fi-table-cell">
                    <div className="flex flex-col">
                      <span className="font-medium">{formatTimestamp(log.timestamp)}</span>
                      <span className="fi-text-xs-muted">
                        {formatTime(log.timestamp)}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded fi-text-xs-medium border ${getOperationBadgeColor(
                        log.operation
                      )}`}
                    >
                      {log.operation}
                    </span>
                  </td>
                  <td className="fi-table-cell">
                    {log.user_id}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded fi-text-xs-medium ${getStatusBadgeColor(
                        log.status
                      )}`}
                    >
                      {log.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <div className="fi-flex-gap">
                      <span className="text-slate-400 font-mono text-xs truncate max-w-xs">
                        {log.endpoint}
                      </span>
                      {sessionId && (
                        <a
                          href={`/sessions/${sessionId}`}
                          onClick={(e) => e.stopPropagation()}
                          className="fi-text-primary hover:text-blue-300 text-xs underline"
                        >
                          View Session
                        </a>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile View */}
      <div className="lg:hidden divide-y divide-slate-700">
        {logs.map((log) => {
          const sessionId = extractSessionId(log.metadata);
          const isSelected = selectedLog?.audit_id === log.audit_id;

          return (
            <div
              key={log.audit_id}
              className={`p-4 hover:bg-slate-700/50 fi-interactive ${
                isSelected ? "bg-slate-700/70" : ""
              }`}
              onClick={() => onSelectLog(log)}
            >
              <div className="flex justify-between items-start mb-2">
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded fi-text-xs-medium border ${getOperationBadgeColor(
                    log.operation
                  )}`}
                >
                  {log.operation}
                </span>
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded fi-text-xs-medium ${getStatusBadgeColor(
                    log.status
                  )}`}
                >
                  {log.status}
                </span>
              </div>

              <div className="text-sm fi-text mb-2">{log.user_id}</div>

              <div className="fi-text-xs-muted mb-2">{formatTimestamp(log.timestamp)}</div>

              <div className="text-xs font-mono text-slate-400 truncate">{log.endpoint}</div>

              {sessionId && (
                <a
                  href={`/sessions/${sessionId}`}
                  onClick={(e) => e.stopPropagation()}
                  className="fi-text-primary hover:text-blue-300 text-xs underline mt-2 inline-block"
                >
                  View Session →
                </a>
              )}
            </div>
          );
        })}
      </div>

      {/* Pagination Note */}
      {logs.length >= 100 && (
        <div className="bg-slate-700 px-4 py-3 text-center fi-subtitle">
          Showing most recent 100 events. Use filters to narrow results.
        </div>
      )}
    </div>
  );
}
