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
    if (currentInterval <= 1000) return { label: 'Fast', color: 'fi-text-success', bg: 'bg-emerald-500/10' };
    if (currentInterval <= 3000) return { label: 'Adaptive', color: 'fi-text-info', bg: 'bg-cyan-500/10' };
    return { label: 'Idle', color: 'text-slate-400', bg: 'bg-slate-500/10' };
  };

  const pollingMode = getPollingMode();

  return (
    <div className="fi-modal-backdrop bg-black/80">
      <div className="w-full max-w-md rounded-xl bg-slate-800 border border-slate-700 p-8 shadow-2xl animate-slide-up">
        {/* Icon / Progress Circle */}
        <div className="flex justify-center mb-6">
          {status === 'completed' ? (
            <div className="relative w-20 h-20">
              {/* SVG Progress Circle - 100% complete */}
              <svg className="w-20 h-20 transform -rotate-90" viewBox="0 0 100 100">
                {/* Background circle */}
                <circle
                  cx="50"
                  cy="50"
                  r="45"
                  stroke="currentColor"
                  strokeWidth="8"
                  fill="none"
                  className="text-slate-700"
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
                  className="text-green-500"
                  strokeDasharray={`${2 * Math.PI * 45}`}
                  strokeDashoffset="0"
                />
              </svg>
              {/* 100% text in center */}
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-xl font-bold fi-text-green">100%</span>
              </div>
            </div>
          ) : status === 'failed' ? (
            <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center">
              <XCircle className="h-8 w-8 fi-text-error" />
            </div>
          ) : (
            <div className="relative w-20 h-20">
              {/* SVG Progress Circle - animated */}
              <svg className="w-20 h-20 transform -rotate-90" viewBox="0 0 100 100">
                {/* Background circle */}
                <circle
                  cx="50"
                  cy="50"
                  r="45"
                  stroke="currentColor"
                  strokeWidth="8"
                  fill="none"
                  className="text-slate-700"
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
                  className="text-emerald-500 transition-all duration-500 ease-out"
                  strokeDasharray={`${2 * Math.PI * 45}`}
                  strokeDashoffset={`${2 * Math.PI * 45 * (1 - (status === 'waiting_for_chunks' ? chunkProgress : progress) / 100)}`}
                />
              </svg>
              {/* Percentage text in center */}
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-xl font-bold fi-text-success">
                  {status === 'waiting_for_chunks' ? chunkProgress : progress}%
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Title */}
        <h2 className="text-xl font-semibold text-white text-center mb-2">
          {status === 'completed'
            ? '¡Diarización Completada!'
            : status === 'failed'
            ? 'Error en Diarización'
            : status === 'waiting_for_chunks'
            ? 'Finalizando Sesión...'
            : 'Procesando Diarización...'}
        </h2>

        {/* Description */}
        <p className="text-slate-400 text-center mb-6">
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
            <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
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
            <p className="text-sm text-slate-500 text-center">
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
          <div className="mt-4 p-3 bg-slate-900/50 rounded-lg border border-yellow-500/50">
            <div className="flex items-center justify-between mb-2">
              <span className="fi-text-xs-medium text-slate-400">Monitor en tiempo real</span>
              <span className={`text-xs px-2 py-0.5 rounded-full ${pollingMode.bg} ${pollingMode.color} font-medium`}>
                {pollingMode.label}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="flex flex-col">
                <span className="text-slate-500 mb-1">Intervalo</span>
                <span className="text-white font-mono font-medium">{intervalSeconds}s</span>
              </div>
              <div className="flex flex-col">
                <span className="text-slate-500 mb-1">Verificaciones</span>
                <span className="text-white font-mono font-medium">{totalPolls}</span>
              </div>
            </div>
            {currentInterval > 1000 && (
              <div className="mt-2 pt-2 fi-border-top/50">
                <p className="fi-text-xs-muted flex items-center gap-1">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
                  Modo adaptativo: reduciendo frecuencia para ahorrar recursos
                </p>
              </div>
            )}
          </div>
        )}

        {/* Info */}
        {status === 'waiting_for_chunks' && (
          <div className="mt-6 p-4 bg-slate-900/50 rounded-lg border border-slate-700">
            <p className="fi-text-xs text-center flex items-center justify-center gap-2">
              <Mic className="w-4 h-4 flex-shrink-0" strokeWidth={1.5} aria-hidden="true" />
              <span><strong>Transcripción en progreso:</strong> Procesando chunks de audio
              con Whisper AI (13 segundos por chunk).</span>
            </p>
          </div>
        )}
        {status === 'in_progress' && (
          <div className="mt-6 p-4 bg-slate-900/50 rounded-lg border border-slate-700">
            <p className="fi-text-xs text-center flex items-center justify-center gap-2">
              <Lightbulb className="w-4 h-4 flex-shrink-0 text-yellow-400" strokeWidth={1.5} aria-hidden="true" />
              <span><strong>Triple Vision:</strong> Analizando 3 fuentes de transcripción
              simultáneamente para máxima precisión.</span>
            </p>
          </div>
        )}

        {/* Error details */}
        {status === 'failed' && error && (
          <div className="mt-4 p-3 bg-red-900/20 rounded-lg border border-red-700/30">
            <p className="text-xs fi-text-error font-mono">{error}</p>
          </div>
        )}

        {/* Note */}
        {status !== 'failed' && status !== 'completed' && (
          <p className="fi-text-xs-muted text-center mt-6">
            Este proceso puede tomar 1-3 minutos dependiendo de la duración del audio.
          </p>
        )}

        {/* Emergency Exit Button (ESC key) */}
        {status !== 'completed' && status !== 'failed' && onCancel && (
          <Button
            onClick={onCancel}
            variant="secondary"
            fullWidth
            className="mt-4"
          >
            Cancelar (ESC)
          </Button>
        )}
      </div>
    </div>
  );
}
