/**
 * Sessions Table Component
 * Card: FI-UI-FEAT-201
 */

import type { Session } from "../types/session";

interface SessionsTableProps {
  sessions: Session[];
  onSelectSession: (sessionId: string) => void;
}

const getStatusBadgeColor = (status: string): string => {
  switch (status) {
    case "active":
      return "bg-green-900/30 fi-text-green";
    case "complete":
      return "bg-blue-900/30 fi-text-primary";
    case "new":
      return "bg-slate-700/30 text-slate-400";
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

export function SessionsTable({ sessions, onSelectSession }: SessionsTableProps) {
  return (
    <div className="bg-slate-800 rounded-lg overflow-hidden">
      {/* Desktop View */}
      <div className="hidden lg:block overflow-x-auto">
        <table className="w-full">
          <thead className="bg-slate-700">
            <tr>
              <th className="fi-table-header">
                Session ID
              </th>
              <th className="fi-table-header">
                Status
              </th>
              <th className="fi-table-header">
                Interactions
              </th>
              <th className="fi-table-header">
                Created
              </th>
              <th className="fi-table-header">
                Last Active
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {sessions.map((session) => (
              <tr
                key={session.id}
                className="hover:bg-slate-700/50 fi-interactive"
                onClick={() => onSelectSession(session.id)}
              >
                <td className="fi-table-cell font-mono">
                  {session.id.substring(0, 12)}...
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded fi-text-xs-medium ${getStatusBadgeColor(
                      session.status
                    )}`}
                  >
                    {session.status.toUpperCase()}
                  </span>
                </td>
                <td className="fi-table-cell">
                  {session.interaction_count}
                </td>
                <td className="fi-table-cell">
                  {formatTimestamp(session.created_at)}
                </td>
                <td className="fi-table-cell">
                  {formatTimestamp(session.last_active)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile View */}
      <div className="lg:hidden divide-y divide-slate-700">
        {sessions.map((session) => (
          <div
            key={session.id}
            className="p-4 hover:bg-slate-700/50 fi-interactive"
            onClick={() => onSelectSession(session.id)}
          >
            <div className="flex justify-between items-start mb-2">
              <span className="text-sm fi-text font-mono">
                {session.id.substring(0, 12)}...
              </span>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded fi-text-xs-medium ${getStatusBadgeColor(
                  session.status
                )}`}
              >
                {session.status.toUpperCase()}
              </span>
            </div>

            <div className="text-sm fi-text mb-2">
              {session.interaction_count} interactions
            </div>

            <div className="fi-text-xs-muted">
              Created {formatTimestamp(session.created_at)} · Last active{" "}
              {formatTimestamp(session.last_active)}
            </div>
          </div>
        ))}
      </div>

      {/* Empty State */}
      {sessions.length === 0 && (
        <div className="fi-empty-state-muted">
          No sessions found
        </div>
      )}
    </div>
  );
}
