/**
 * SessionList Component
 *
 * SOLID Principles:
 * - Single Responsibility: Manages session list + filters
 * - Open/Closed: Extensible via props and render functions
 *
 * @example
 * <SessionList
 *   sessions={sessionsData}
 *   onSelectSession={(id) => loadSession(id)}
 *   onDeleteSession={(id) => deleteSession(id)}
 * />
 */

import React, { useState } from 'react';
import { History } from 'lucide-react';
import { SessionSummary, SessionTaskStatus, SessionFilter } from '@aurity-standalone/types/patient';
import { SessionCard } from './SessionCard';

export interface SessionListProps {
  sessions: SessionSummary[];
  sessionStatuses: Record<string, SessionTaskStatus>;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onCopySessionId: (sessionId: string, e: React.MouseEvent) => void;
  copiedSessionId: string | null;
  loading?: boolean;
  extractMedicalInfo: (preview: string) => string[];
  title?: string;
  subtitle?: string;
  className?: string;
}

export const SessionList: React.FC<SessionListProps> = ({
  sessions,
  sessionStatuses,
  onSelectSession,
  onDeleteSession,
  onCopySessionId,
  copiedSessionId,
  loading = false,
  extractMedicalInfo,
  title = 'Consultas Anteriores',
  subtitle = 'Continúa una sesión',
  className = ''
}) => {
  const [filter, setFilter] = useState<SessionFilter>('all');

  return (
    <div className={`bg-slate-900/50 backdrop-blur-sm border border-slate-800/50 rounded-2xl p-6 shadow-xl sticky top-24 ${className}`}>
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="fi-icon-gradient-cyan">
          <History className="h-6 w-6 fi-text-info" />
        </div>
        <div className="flex-1">
          <h2 className="text-lg font-bold text-white">{title}</h2>
          <p className="fi-subtitle">{subtitle}</p>
        </div>
      </div>

      {/* Session Filters */}
      <div className="flex gap-2 mb-4">
        {(['all', 'today', 'week'] as SessionFilter[]).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={filter === f ? 'fi-filter-btn-cyan' : 'fi-filter-btn'}
          >
            {f === 'all' ? 'Todas' : f === 'today' ? 'Hoy' : 'Semana'}
          </button>
        ))}
      </div>

      {/* Sessions */}
      {loading ? (
        <div className="fi-empty-state">
          <div className="animate-spin h-10 w-10 border-4 border-cyan-500 border-t-transparent rounded-full mb-3" />
          <span className="fi-subtitle">Cargando sesiones...</span>
        </div>
      ) : sessions.length === 0 ? (
        <div className="py-12 text-center">
          <History className="h-12 w-12 text-slate-600 mx-auto mb-3" />
          <p className="fi-subtitle">No hay consultas previas</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
          {sessions.slice(0, 10).map((session) => {
            const sessionId = session.metadata.session_id;
            const status = sessionStatuses[sessionId] || {
              soapStatus: 'not_started' as const,
              diarizationStatus: 'not_started' as const
            };

            return (
              <SessionCard
                key={sessionId}
                session={session}
                status={status}
                onSelect={onSelectSession}
                onDelete={onDeleteSession}
                onCopyId={onCopySessionId}
                copiedSessionId={copiedSessionId}
                extractMedicalInfo={extractMedicalInfo}
              />
            );
          })}
        </div>
      )}
    </div>
  );
};
