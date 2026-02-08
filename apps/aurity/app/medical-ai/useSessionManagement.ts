/**
 * useSessionManagement - Session state management hook
 *
 * Handles session list, selection, deletion, and status tracking
 */

import { useState, useEffect } from 'react';
import { SessionSummary, SessionTaskStatus, TaskStatus } from '@aurity-standalone/types/patient';
import { getSessionSummaries } from '@aurity-standalone/api-client/timeline';
import { toastError } from '@/lib/swal';
import { api } from '@/lib/api/client';
import { ROUTES } from '@/lib/api/routes';

export function useSessionManagement() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  const [isExistingSession, setIsExistingSession] = useState(false);
  const [sessionDuration, setSessionDuration] = useState<string>('');
  const [copiedSessionId, setCopiedSessionId] = useState<string | null>(null);
  const [deleteConfirmSession, setDeleteConfirmSession] = useState<string | null>(null);
  const [deletingSession, setDeletingSession] = useState<string | null>(null);
  const [sessionStatuses, setSessionStatuses] = useState<Record<string, SessionTaskStatus>>({});

  // Load sessions on mount
  useEffect(() => {
    async function loadSessions() {
      try {
        setLoadingSessions(true);
        const summaries = await getSessionSummaries();
        setSessions(summaries);

        // Load statuses for sessions
        await loadSessionStatuses(summaries.map(s => s.metadata.session_id));
      } catch {
        // Silent fail - sessions will remain empty
      } finally {
        setLoadingSessions(false);
      }
    }

    loadSessions();
  }, []);

  // Load session statuses (SOAP, Diarization)
  const loadSessionStatuses = async (sessionIds: string[]) => {
    const statusesMap: Record<string, SessionTaskStatus> = {};

    await Promise.all(
      sessionIds.map(async (sessionId) => {
        try {
          const data = await api.get<{
            soap?: { status: string };
            diarization?: { status: string };
          }>(`${ROUTES.medicalAi}/sessions/${sessionId}/monitor`, {
            timeout: 5000,
          });

          statusesMap[sessionId] = {
            soapStatus: (data.soap?.status as TaskStatus) || 'not_started',
            diarizationStatus: (data.diarization?.status as TaskStatus) || 'not_started',
          };
        } catch {
          // Silently fail - status will remain not_started
        }
      })
    );

    setSessionStatuses(statusesMap);
  };

  // Handle delete session
  const handleDeleteSession = async (sessionId: string) => {
    try {
      setDeletingSession(sessionId);

      // TODO: Call backend delete endpoint when implemented
      // For now, just remove from local state
      setSessions((prev) => prev.filter((s) => s.metadata.session_id !== sessionId));

      setDeleteConfirmSession(null);
    } catch {
      toastError('Error al eliminar la sesión');
    } finally {
      setDeletingSession(null);
    }
  };

  // Handle selecting existing session
  const handleSelectSession = (sessionId: string) => {
    const selectedSession = sessions.find((s) => s.metadata.session_id === sessionId);
    const duration = selectedSession?.timespan?.duration_human || '00:00';

    setCurrentSessionId(sessionId);
    setIsExistingSession(true);
    setSessionDuration(duration);
  };

  // Copy session ID to clipboard
  const handleCopySessionId = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(sessionId);
      setCopiedSessionId(sessionId);
      setTimeout(() => setCopiedSessionId(null), 2000);
    } catch {
      // Clipboard API may fail silently in some browsers
    }
  };

  return {
    sessions,
    loadingSessions,
    currentSessionId,
    setCurrentSessionId,
    isExistingSession,
    setIsExistingSession,
    sessionDuration,
    setSessionDuration,
    copiedSessionId,
    deleteConfirmSession,
    setDeleteConfirmSession,
    deletingSession,
    sessionStatuses,
    handleDeleteSession,
    handleSelectSession,
    handleCopySessionId,
  };
}
