/**
 * Free Intelligence - Sessions Table Component
 *
 * Presentational component for sessions list.
 *
 * File: apps/aurity/ui/components/SessionsTable.tsx
 * Card: FI-UI-FEAT-201
 * Created: 2025-10-29
 */

import type { Session } from "../types/session";

interface SessionsTableProps {
  sessions: Session[];
  onSelectSession?: (sessionId: string) => void;
}

export function SessionsTable({
  sessions,
  onSelectSession,
}: SessionsTableProps) {
  const formatDate = (isoDate: string) => {
    const date = new Date(isoDate);
    return date.toLocaleString();
  };

  const getStatusBadge = (status: string) => {
    const colors = {
      new: "bg-blue-900/40 text-blue-300 border border-blue-700",
      active: "bg-green-900/40 text-green-300 border border-green-700",
      complete: "bg-slate-700 text-slate-300 border border-slate-600",
    };
    return colors[status as keyof typeof colors] || "bg-slate-700 text-slate-300 border border-slate-600";
  };

  if (sessions.length === 0) {
    return (
      <div className="text-center py-12 text-slate-400">
        No sessions found. Create your first session to get started.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-700">
        <thead className="bg-slate-800">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
              Session ID
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
              Created
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
              Last Active
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
              Interactions
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
              Status
            </th>
          </tr>
        </thead>
        <tbody className="bg-slate-800 divide-y divide-slate-700">
          {sessions.map((session) => (
            <tr
              key={session.id}
              onClick={() => onSelectSession?.(session.id)}
              className="hover:bg-slate-750 cursor-pointer transition-colors"
            >
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-200">
                {session.id.substring(0, 12)}...
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">
                {formatDate(session.created_at)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">
                {formatDate(session.last_active)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">
                {session.interaction_count}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span
                  className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadge(
                    session.status
                  )}`}
                >
                  {session.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
