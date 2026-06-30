'use client';

// B3-VOICE-FIGLASS-9 — Single audio artifact row in the queue panel.

import { useState, useCallback } from 'react';
import {
  Mic,
  PauseCircle,
  CheckCircle2,
  CheckCheck,
  AlertCircle,
  Loader2,
  Play,
  RotateCcw,
  Trash2,
  FileAudio,
} from 'lucide-react';
import type { AudioArtifact } from './audioArtifact';
import {
  artifactLabel,
  formatArtifactSize,
  formatArtifactDuration,
} from './audioArtifact';

export interface AudioQueueItemProps {
  artifact: AudioArtifact;
  onTranscribe?: (id: string) => void;
  onRetry?: (id: string) => void;
  onDelete?: (id: string) => void;
  /** Mark a transcribed artifact as used/sent — hides it from the queue
   * without deleting the audio. */
  onArchive?: (id: string) => void;
  onGetPlaybackUrl?: (id: string) => Promise<string | null>;
  className?: string;
}

function StateIcon({ state }: { state: AudioArtifact['state'] }) {
  const base = 'w-4 h-4 shrink-0';
  switch (state) {
    case 'recording':
      return <Mic className={`${base} text-red-400 animate-pulse`} />;
    case 'paused':
      return <PauseCircle className={`${base} text-yellow-400`} />;
    case 'stopping':
      return <Loader2 className={`${base} text-amber-400 animate-spin`} />;
    case 'transcribed':
      return <CheckCircle2 className={`${base} text-green-400`} />;
    case 'failed':
      return <AlertCircle className={`${base} text-red-400`} />;
    case 'transcribing':
    case 'uploading':
      return <Loader2 className={`${base} text-blue-400 animate-spin`} />;
    default:
      return <FileAudio className={`${base} text-gray-400`} />;
  }
}

export function AudioQueueItem({
  artifact,
  onTranscribe,
  onRetry,
  onDelete,
  onArchive,
  onGetPlaybackUrl,
  className = '',
}: AudioQueueItemProps) {
  const [playing, setPlaying] = useState(false);
  const [audioEl, setAudioEl] = useState<HTMLAudioElement | null>(null);

  const handlePlay = useCallback(async () => {
    if (!onGetPlaybackUrl) return;
    if (playing && audioEl) {
      audioEl.pause();
      setPlaying(false);
      return;
    }
    const url = await onGetPlaybackUrl(artifact.id);
    if (!url) return;
    const el = new Audio(url);
    setAudioEl(el);
    setPlaying(true);
    el.play().catch(() => setPlaying(false));
    el.addEventListener('ended', () => {
      setPlaying(false);
      URL.revokeObjectURL(url);
    });
    el.addEventListener('error', () => {
      setPlaying(false);
      URL.revokeObjectURL(url);
    });
  }, [artifact.id, onGetPlaybackUrl, playing, audioEl]);

  const canTranscribe =
    artifact.state === 'queued' || artifact.state === 'saved';
  const canRetry = artifact.state === 'failed';
  const canPlay =
    !!onGetPlaybackUrl &&
    artifact.size > 0 &&
    artifact.state !== 'recording' &&
    artifact.state !== 'paused';
  const isBusy =
    artifact.state === 'transcribing' || artifact.state === 'uploading';

  return (
    <div
      className={`flex items-start gap-3 p-3 rounded-lg bg-white/5 border border-white/10 ${className}`}
    >
      <StateIcon state={artifact.state} />

      <div className="flex-1 min-w-0 space-y-0.5">
        <div className="flex items-center gap-2 text-xs">
          <span className="font-medium text-white/80">
            {artifactLabel(artifact.state)}
          </span>
          <span className="text-white/40">·</span>
          <span className="text-white/50">
            {formatArtifactDuration(artifact.durationMs)}
          </span>
          <span className="text-white/40">·</span>
          <span className="text-white/50">{formatArtifactSize(artifact.size)}</span>
        </div>

        {artifact.state === 'transcribed' && artifact.transcript && (
          <p className="text-xs text-white/60 truncate">{artifact.transcript}</p>
        )}
        {artifact.state === 'failed' && artifact.errorMessage && (
          <p className="text-xs text-red-400/80 truncate">{artifact.errorMessage}</p>
        )}
        <p className="text-[10px] text-white/30">
          {new Date(artifact.createdAt).toLocaleString('es-MX', {
            hour: '2-digit',
            minute: '2-digit',
            day: 'numeric',
            month: 'short',
          })}
        </p>
      </div>

      <div className="flex items-center gap-1 shrink-0">
        {canPlay && (
          <button
            onClick={handlePlay}
            disabled={isBusy}
            className="p-1.5 rounded-md hover:bg-white/10 text-white/50 hover:text-white/80 transition-colors"
            aria-label={playing ? 'Pausar' : 'Reproducir'}
          >
            <Play className="w-3.5 h-3.5" />
          </button>
        )}
        {canTranscribe && onTranscribe && (
          <button
            onClick={() => onTranscribe(artifact.id)}
            disabled={isBusy}
            className="px-2 py-1 rounded-md text-xs bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 transition-colors"
          >
            Transcribir
          </button>
        )}
        {canRetry && onRetry && (
          <button
            onClick={() => onRetry(artifact.id)}
            className="p-1.5 rounded-md hover:bg-white/10 text-yellow-400/70 hover:text-yellow-400 transition-colors"
            aria-label="Reintentar transcripción"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        )}
        {artifact.state === 'transcribed' && onArchive && (
          <button
            onClick={() => onArchive(artifact.id)}
            className="fi-audio-item-archive p-1.5 rounded-md hover:bg-white/10 text-emerald-400/60 hover:text-emerald-400 transition-colors"
            aria-label="Marcar como enviado al chat"
            title="Marcar como enviado al chat"
          >
            <CheckCheck className="w-3.5 h-3.5" />
          </button>
        )}
        {onDelete && artifact.state !== 'recording' && artifact.state !== 'paused' && (
          <button
            onClick={() => onDelete(artifact.id)}
            disabled={isBusy}
            className="p-1.5 rounded-md hover:bg-white/10 text-white/30 hover:text-red-400 transition-colors"
            aria-label="Eliminar audio"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}
