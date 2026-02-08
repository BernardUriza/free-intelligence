/**
 * Diarization Processing Modal
 *
 * Blocking modal that shows diarization progress while polling
 * ESC key support added (2025-11-15) for emergency exit
 *
 * Author: Bernard Uriza Orozco
 * Created: 2025-11-14
 * Updated: 2025-11-15 (ESC key support)
 */

import React, { useEffect } from 'react';
import { XCircle, Mic, Lightbulb } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface DiarizationProcessingModalProps {
  isOpen: boolean;
  status: 'waiting_for_chunks' | 'pending' | 'in_progress' | 'completed' | 'failed';
  progress: number;
  segmentCount?: number;
  error?: string;
  statusMessage?: string; // Detailed message from polling
  // Chunk transcription progress (for waiting_for_chunks state)
  completedChunks?: number;
  totalChunks?: number;
  estimatedSecondsRemaining?: number; // Time estimate for transcription
  // Adaptive polling metrics
  currentInterval?: number; // Current polling interval (ms)
  totalPolls?: number; // Total polls attempted
  isPolling?: boolean; // Whether polling is active
  // Emergency exit callback
  onCancel?: () => void; // Called when user presses ESC or clicks cancel button
}

export function DiarizationProcessingModal({
  isOpen,
  status,
  progress,
  segmentCount,
  error,
  statusMessage,
  completedChunks = 0,
  totalChunks = 0,
  estimatedSecondsRemaining = 0,
  currentInterval = 1000,
  totalPolls = 0,
  isPolling: _isPolling = false,
  onCancel,
}: DiarizationProcessingModalProps) {
  // ESC key listener for emergency exit
  useEffect(() => {
    if (!isOpen || !onCancel) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        console.log('[DiarizationModal] ESC pressed - emergency exit');
        onCancel();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  // Calculate chunk progress percentage
  const chunkProgress = totalChunks > 0 ? Math.round((completedChunks / totalChunks) * 100) : 0;

  // Format interval for display
  const intervalSeconds = (currentInterval / 1000).toFixed(1);

  // Determine polling mode (fast/adaptive/idle)
  const getPollingMode = () => {
    if (currentInterval <= 1000) return { label: 'Fast', className: 'diar-mode-fast' };
    if (currentInterval <= 3000) return { label: 'Adaptive', className: 'diar-mode-adaptive' };
    return { label: 'Idle', className: 'diar-mode-idle' };
  };

  const pollingMode = getPollingMode();

  return (
    <div className="diar-backdrop">
      <div className="diar-modal">
        {/* Icon / Progress Circle */}
        <div className="diar-circle-wrap">
          {status === 'completed' ? (
            <div className="diar-circle-container">
              {/* SVG Progress Circle - 100% complete */}
              <svg className="diar-circle-svg" viewBox="0 0 100 100">
                {/* Background circle */}
                <circle
                  cx="50"
                  cy="50"
                  r="45"
                  stroke="currentColor"
                  strokeWidth="8"
                  fill="none"
                  className="diar-circle-bg"
                />
                {/* Progress circle - full green */}
                <circle
                  cx="50"
                  cy="50"
                  r="45"
                  stroke="currentColor"
                  strokeWidth="8"
                  fill="none"
                  strokeLinecap="round"
                  className="diar-circle-complete"
                  strokeDasharray={`${2 * Math.PI * 45}`}
                  strokeDashoffset="0"
                />
              </svg>
              {/* 100% text in center */}
              <div className="diar-circle-center">
                <span className="diar-circle-pct fi-text-green">100%</span>
              </div>
            </div>
          ) : status === 'failed' ? (
            <div className="diar-fail-icon-wrap">
              <XCircle className="diar-fail-icon fi-text-error" />
            </div>
          ) : (
            <div className="diar-circle-container">
              {/* SVG Progress Circle - animated */}
              <svg className="diar-circle-svg" viewBox="0 0 100 100">
                {/* Background circle */}
                <circle
                  cx="50"
                  cy="50"
                  r="45"
                  stroke="currentColor"
                  strokeWidth="8"
                  fill="none"
                  className="diar-circle-bg"
                />
                {/* Progress circle */}
                <circle
                  cx="50"
                  cy="50"
                  r="45"
                  stroke="currentColor"
                  strokeWidth="8"
                  fill="none"
                  strokeLinecap="round"
                  className="diar-circle-progress"
                  strokeDasharray={`${2 * Math.PI * 45}`}
                  strokeDashoffset={`${2 * Math.PI * 45 * (1 - (status === 'waiting_for_chunks' ? chunkProgress : progress) / 100)}`}
                />
              </svg>
              {/* Percentage text in center */}
              <div className="diar-circle-center">
                <span className="diar-circle-pct fi-text-success">
                  {status === 'waiting_for_chunks' ? chunkProgress : progress}%
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Title */}
        <h2 className="diar-title">
          {status === 'completed'
            ? '¡Diarización Completada!'
            : status === 'failed'
            ? 'Error en Diarización'
            : status === 'waiting_for_chunks'
            ? 'Finalizando Sesión...'
            : 'Procesando Diarización...'}
        </h2>

        {/* Description */}
        <p className="diar-description">
          {status === 'completed'
            ? `Se identificaron ${segmentCount || 0} segmentos con clasificación de hablantes.`
            : status === 'failed'
            ? error || 'Ocurrió un error al procesar la diarización.'
            : status === 'waiting_for_chunks'
            ? `Transcribiendo audio: ${completedChunks}/${totalChunks} chunks completados`
            : statusMessage || 'Analizando el audio con IA para identificar y clasificar hablantes (MEDICO/PACIENTE).'}
        </p>

        {/* Progress bar */}
        {status !== 'failed' && status !== 'completed' && (
          <div className="fi-stack-md">
            <div className="diar-progress-track">
              <div
                className="fi-progress-bar duration-500 ease-out"
                style={{
                  width: `${Math.min(
                    status === 'waiting_for_chunks' ? chunkProgress : progress,
                    100
                  )}%`
                }}
              />
            </div>
            <p className="diar-progress-label">
              {status === 'waiting_for_chunks'
                ? estimatedSecondsRemaining > 0
                  ? `${chunkProgress}% completado (${completedChunks}/${totalChunks} chunks) · ~${estimatedSecondsRemaining}s restantes`
                  : `${chunkProgress}% completado (${completedChunks}/${totalChunks} chunks)`
                : `${progress}% completado`}
            </p>
          </div>
        )}

        {/* Adaptive Polling Metrics - ALWAYS VISIBLE FOR DEBUG */}
        {status !== 'completed' && status !== 'failed' && (
          <div className="diar-metrics-panel">
            <div className="diar-metrics-header">
              <span className="fi-text-xs-medium">Monitor en tiempo real</span>
              <span className={`diar-metrics-mode-badge ${pollingMode.className}`}>
                {pollingMode.label}
              </span>
            </div>
            <div className="diar-metrics-grid">
              <div className="diar-metrics-col">
                <span className="diar-metrics-label">Intervalo</span>
                <span className="diar-metrics-value">{intervalSeconds}s</span>
              </div>
              <div className="diar-metrics-col">
                <span className="diar-metrics-label">Verificaciones</span>
                <span className="diar-metrics-value">{totalPolls}</span>
              </div>
            </div>
            {currentInterval > 1000 && (
              <div className="mt-2 pt-2 fi-border-top/50">
                <p className="fi-text-xs-muted flex items-center gap-1">
                  <span className="diar-metrics-adaptive"></span>
                  Modo adaptativo: reduciendo frecuencia para ahorrar recursos
                </p>
              </div>
            )}
          </div>
        )}

        {/* Info */}
        {status === 'waiting_for_chunks' && (
          <div className="diar-info-box">
            <p className="fi-text-xs diar-info-text">
              <Mic className="diar-info-icon" strokeWidth={1.5} aria-hidden="true" />
              <span><strong>Transcripción en progreso:</strong> Procesando chunks de audio
              con Whisper AI (13 segundos por chunk).</span>
            </p>
          </div>
        )}
        {status === 'in_progress' && (
          <div className="diar-info-box">
            <p className="fi-text-xs diar-info-text">
              <Lightbulb className="diar-info-icon-yellow" strokeWidth={1.5} aria-hidden="true" />
              <span><strong>Triple Vision:</strong> Analizando 3 fuentes de transcripción
              simultáneamente para máxima precisión.</span>
            </p>
          </div>
        )}

        {/* Error details */}
        {status === 'failed' && error && (
          <div className="diar-error-box">
            <p className="diar-error-text fi-text-error">{error}</p>
          </div>
        )}

        {/* Note */}
        {status !== 'failed' && status !== 'completed' && (
          <p className="fi-text-xs-muted diar-note">
            Este proceso puede tomar 1-3 minutos dependiendo de la duración del audio.
          </p>
        )}

        {/* Emergency Exit Button (ESC key) */}
        {status !== 'completed' && status !== 'failed' && onCancel && (
          <Button
            onClick={onCancel}
            variant="secondary"
            fullWidth
            className="diar-cancel-btn"
          >
            Cancelar (ESC)
          </Button>
        )}
      </div>
    </div>
  );
}
