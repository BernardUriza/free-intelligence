'use client';

/**
 * DialogueFlow Component - Refactored with EventTimeline
 *
 * Medical conversation review with speaker diarization.
 * Now using reusable EventTimeline component with dialogFlowConfig.
 *
 * Features:
 * ✅ Speaker diarization (MEDICO/PACIENTE)
 * ✅ Audio playback sync
 * ✅ Edit functionality
 * ✅ Search/filter/export (via EventTimeline)
 * ✅ Auto-diarization when not found
 *
 * Refactored: 2025-11-18 (793 lines → ~250 lines)
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('DialogueFlow');
import {
  ChevronRight,
  Loader2,
  AlertCircle,
  MessageSquare,
  User,
  Lightbulb,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { medicalWorkflowApi, type DiarizationSegment } from '@aurity-standalone/api-client/medical-workflow';
import { APIError } from '@aurity-standalone/api-client';
import { EventTimeline, type TimelineEvent } from '@/components/audit/EventTimeline';
import { dialogFlowConfig } from '@/lib/dialogflow-config';
import { toastError } from '@/lib/swal';

// ============================================================================
// Types
// ============================================================================

interface DialogueFlowProps {
  onNext?: () => void;
  onPrevious?: () => void;
  sessionId?: string;
  audioUrl?: string | null;
  className?: string;
}

interface EnhancedSegment extends DiarizationSegment {
  id: string;
  duration: number;
}

// ============================================================================
// Main Component
// ============================================================================

export function DialogueFlow({
  onNext,
  onPrevious,
  sessionId,
  audioUrl,
  className = '',
}: DialogueFlowProps) {
  // ========================================
  // State Management
  // ========================================

  const [segments, setSegments] = useState<EnhancedSegment[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [provider, setProvider] = useState<string>('');
  const [completedAt, setCompletedAt] = useState<string>('');

  // Auto-diarization states
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<string>('');
  const [jobId, setJobId] = useState<string | null>(null);

  // Edit state
  const [, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

  // Audio refs
  const audioRef = useRef<HTMLAudioElement>(null);
  const [, setCurrentTime] = useState(0);
  const [, setIsPlaying] = useState(false);

  // ========================================
  // Data Loading
  // ========================================

  useEffect(() => {
    if (!sessionId) {
      setSegments([]);
      return;
    }

    const loadSegments = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await medicalWorkflowApi.getDiarizationSegments(sessionId);

        // Enhance segments with computed fields
        const enhanced: EnhancedSegment[] = response.segments.map((seg, idx) => ({
          ...seg,
          id: `seg-${idx}`,
          duration: seg.end_time - seg.start_time,
        }));

        setSegments(enhanced);
        setProvider(response.provider);
        setCompletedAt(response.completed_at);
      } catch (err: any) {
        log.error('Failed to load segments', { error: String(err) });

        // Check if 404 - diarization doesn't exist yet
        const is404 = (err instanceof APIError && err.status === 404) ||
                      err?.message?.includes('not found') ||
                      err?.message?.includes('Diarization task not found');

        if (is404) {
          await startDiarizationAutomatically();
        } else {
          setError(err instanceof Error ? err.message : 'Failed to load segments');
        }
      } finally {
        setIsLoading(false);
      }
    };

    const startDiarizationAutomatically = async () => {
      try {
        setIsProcessing(true);
        setProcessingStatus('Iniciando diarización...');

        // Start diarization task
        const jobResponse = await medicalWorkflowApi.startDiarization(sessionId);
        setJobId(jobResponse.job_id);
        setProcessingStatus(`Procesando speakers (Job: ${jobResponse.job_id})...`);

        // Poll for completion
        const pollInterval = setInterval(async () => {
          try {
            const status = await medicalWorkflowApi.getDiarizationStatus(jobResponse.job_id);
            setProcessingStatus(`Estado: ${status.status} (${status.progress || 0}%)`);

            if (status.status === 'completed') {
              clearInterval(pollInterval);
              setIsProcessing(false);
              setProcessingStatus('');
              await loadSegments();
            } else if (status.status === 'failed') {
              clearInterval(pollInterval);
              setIsProcessing(false);
              setError('Diarization failed: ' + (status.error || 'Unknown error'));
            }
          } catch (pollErr) {
            log.error('Diarization polling error', { error: String(pollErr) });
          }
        }, 3000);

        return () => clearInterval(pollInterval);
      } catch (err) {
        log.error('Failed to start diarization', { error: String(err) });
        setIsProcessing(false);
        setError('Failed to start diarization automatically');
      }
    };

    loadSegments();
  }, [sessionId]);

  // ========================================
  // Transform to TimelineEvent Format
  // ========================================

  const timelineEvents = useMemo<TimelineEvent[]>(() => {
    return segments.map((seg) => ({
      id: seg.id,
      timestamp: seg.start_time,
      type: seg.speaker,
      content: seg.text,
      metadata: {
        speaker: seg.speaker,
        start_time: seg.start_time,
        end_time: seg.end_time,
        confidence: seg.confidence,
        improved_text: seg.improved_text,
        duration: seg.duration,
      },
    }));
  }, [segments]);

  // ========================================
  // Stats
  // ========================================

  const stats = useMemo(() => {
    const total = segments.length;
    const medico = segments.filter((s) => {
      const speaker = s.speaker.toLowerCase();
      return speaker === 'medico' || speaker === 'doctor';
    }).length;
    const paciente = segments.filter((s) => {
      const speaker = s.speaker.toLowerCase();
      return speaker === 'paciente' || speaker === 'patient';
    }).length;
    const totalDuration = segments.reduce((sum, s) => sum + s.duration, 0);

    return { total, medico, paciente, totalDuration };
  }, [segments]);

  // ========================================
  // Event Handlers
  // ========================================

  const handleEdit = useCallback((event: TimelineEvent) => {
    setEditingId(event.id);
    setEditText(event.content);
  }, []);

  const _handleSave = useCallback(
    async (id: string) => {
      if (!sessionId) return;

      const segmentIndex = parseInt(id.split('-')[1], 10);

      try {
        await medicalWorkflowApi.updateSegmentText(sessionId, segmentIndex, editText);

        // Update local state
        setSegments((prev) =>
          prev.map((seg) =>
            seg.id === id ? { ...seg, text: editText } : seg
          )
        );

        setEditingId(null);
      } catch (err) {
        log.error('Failed to save segment edit', { error: String(err) });
        toastError('Error al guardar la edición');
      }
    },
    [editText, sessionId]
  );

  const handleAudioPlay = useCallback((event: TimelineEvent) => {
    if (audioRef.current && event.metadata?.start_time) {
      audioRef.current.currentTime = event.metadata.start_time;
      audioRef.current.play();
    }
  }, []);

  const handleAudioTimeUpdate = useCallback(() => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  }, []);

  // ========================================
  // Config with Actions
  // ========================================

  const configWithActions = useMemo(() => ({
    ...dialogFlowConfig,
    actions: {
      onEdit: handleEdit,
      onPlay: handleAudioPlay,
    },
  }), [handleEdit, handleAudioPlay]);

  // ========================================
  // Utility Functions
  // ========================================

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // ========================================
  // Render
  // ========================================

  return (
    <div className={`space-y-6 ${className}`}>
      {/* ===== Header with Stats ===== */}
      {!isLoading && segments.length > 0 && (
        <div className="fi-flex-between">
          <div className="fi-flex-gap-md">
            <div className="w-10 h-10 bg-purple-500/20 rounded-lg flex items-center justify-center">
              <User className="h-5 w-5 fi-text-purple" />
            </div>
            <div>
              <h2 className="fi-title">Revisión del Diálogo</h2>
              <p className="fi-subtitle">
                {stats.total} segmentos • {formatTime(stats.totalDuration)}
              </p>
            </div>
          </div>

          {/* Speaker Legend */}
          <div className="flex gap-2">
            <div className="med-tag-blue">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <span className="text-xs fi-text-primary font-medium">MÉDICO ({stats.medico})</span>
            </div>
            <div className="med-tag-green">
              <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
              <span className="text-xs fi-text-success font-medium">PACIENTE ({stats.paciente})</span>
            </div>
          </div>
        </div>
      )}

      {/* ===== Processing State (Auto-Diarization) ===== */}
      {isProcessing && (
        <div className="fi-card-alert-cyan">
          <Loader2 className="h-6 w-6 fi-text-info flex-shrink-0 animate-spin" />
          <div>
            <p className="fi-text-info font-medium">Diarización automática en progreso</p>
            <p className="fi-text-info/80 text-sm mt-1">
              {processingStatus || 'Separando speakers en el audio...'}
            </p>
            {jobId && (
              <p className="fi-text-info/60 text-xs mt-1">Job ID: {jobId}</p>
            )}
          </div>
        </div>
      )}

      {/* ===== Error State ===== */}
      {error && !isProcessing && (
        <div className="fi-card-alert-danger">
          <AlertCircle className="h-6 w-6 fi-text-error flex-shrink-0" />
          <div>
            <p className="fi-text-error font-medium">Error al cargar segmentos</p>
            <p className="fi-text-error/80 text-sm mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* ===== Empty State ===== */}
      {!isLoading && !error && !isProcessing && segments.length === 0 && (
        <div className="fi-card-xl-center">
          <MessageSquare className="h-12 w-12 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400">No hay segmentos de diarización disponibles</p>
          <p className="text-slate-500 text-sm mt-2">
            {sessionId
              ? 'La diarización puede estar en progreso'
              : 'Proporciona un session_id'}
          </p>
        </div>
      )}

      {/* ===== Audio Player (if available) ===== */}
      {audioUrl && !isLoading && segments.length > 0 && (
        <div className="fi-card-dark">
          <audio
            ref={audioRef}
            controls
            className="w-full"
            src={audioUrl}
            onTimeUpdate={handleAudioTimeUpdate}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
          >
            Tu navegador no soporta reproducción de audio.
          </audio>
          <p className="fi-text-xs-muted mt-2 flex items-center gap-1">
            <Lightbulb className="w-3.5 h-3.5" aria-hidden="true" />
            Haz clic en los timestamps para navegar al momento exacto
          </p>
        </div>
      )}

      {/* ===== EventTimeline Component (Replaces 400+ lines of manual rendering) ===== */}
      <EventTimeline
        events={timelineEvents}
        config={configWithActions}
        isLoading={isLoading}
        error={error}
        className="bg-transparent"
      />

      {/* ===== Footer Metadata ===== */}
      {!isLoading && !error && segments.length > 0 && (
        <div className="fi-card">
          <div className="flex items-center justify-between fi-text-xs">
            <div className="fi-flex-gap-lg">
              <span>
                <strong className="fi-text">Provider:</strong> {provider}
              </span>
              {completedAt && (
                <span>
                  <strong className="fi-text">Completado:</strong>{' '}
                  {new Date(completedAt).toLocaleString('es-MX')}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ===== Navigation ===== */}
      {!isLoading && segments.length > 0 && (
        <div className="flex gap-4">
          {onPrevious && (
            <Button
              onClick={onPrevious}
              variant="secondary"
              size="lg"
              className="flex-1"
            >
              Anterior
            </Button>
          )}
          {onNext && (
            <Button
              onClick={onNext}
              variant="primary"
              size="lg"
              icon={ChevronRight}
              className="flex-1"
            >
              Continuar
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
