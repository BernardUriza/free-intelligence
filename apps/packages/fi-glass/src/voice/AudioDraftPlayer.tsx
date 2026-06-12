'use client';

// B3-VOICE-FIGLASS-10 — Inline audio draft player.
//
// When a recording stops, the freshly-saved artifact becomes a DRAFT shown
// inline in the composer (the WhatsApp pattern: record -> stop -> preview),
// instead of disappearing into a separate queue panel. The user can play it
// back, discard it, or run the primary action (transcribe / send / use).
//
// FRAMEWORK-FIRST (framework-first-canary): this is a reusable fi-glass
// primitive. The primary action is configurable (primaryActionLabel) because
// WhatsApp sends audio AS a message while og118 transcribes it — the component
// never assumes the verb. The consumer wires the callbacks; the AudioQueuePanel
// stays for the extended backlog of older/failed artifacts.

import { useState, useCallback, useEffect } from 'react';
import { Play, Pause, Trash2, Loader2, RotateCcw, ArrowUp, CirclePause } from 'lucide-react';
import type { AudioArtifact } from './audioArtifact';
import { formatArtifactDuration, formatArtifactSize } from './audioArtifact';

export interface AudioDraftPlayerProps {
  /** The draft artifact (the just-recorded, not-yet-acted-on audio). */
  artifact: AudioArtifact;
  /** Resolve a playback object URL for the artifact (caller revokes). */
  onGetPlaybackUrl?: (id: string) => Promise<string | null>;
  /** Primary action — transcribe / send / use the draft. */
  onPrimary?: (id: string) => void;
  /** Discard the draft (deletes the real artifact). */
  onDiscard?: (id: string) => void;
  /** Retry a failed primary action. */
  onRetry?: (id: string) => void;
  /** Resume a paused recording. When provided, a Resume button replaces the
   * primary action (the user hasn't finished recording yet). */
  onResume?: () => void;
  /** Label for the primary action button (default: "Transcribir"). */
  primaryActionLabel?: string;
  className?: string;
}

// Static decorative bars — the durable queue stores no per-sample waveform, so
// these are a fixed visual motif (not real amplitudes). Deterministic heights
// keep the SSR/CSR markup identical (no Math.random at module/render time).
const BAR_HEIGHTS = [
  0.4, 0.7, 0.5, 0.9, 0.6, 0.8, 0.45, 1.0, 0.55, 0.75,
  0.5, 0.85, 0.4, 0.65, 0.7, 0.5, 0.9, 0.6, 0.45, 0.8,
];

export function AudioDraftPlayer({
  artifact,
  onGetPlaybackUrl,
  onPrimary,
  onDiscard,
  onRetry,
  onResume,
  primaryActionLabel = 'Transcribir',
  className = '',
}: AudioDraftPlayerProps) {
  const [playing, setPlaying] = useState(false);
  const [audioEl, setAudioEl] = useState<HTMLAudioElement | null>(null);

  // Stop playback if the artifact transitions out of a playable state.
  useEffect(() => {
    return () => {
      audioEl?.pause();
    };
  }, [audioEl]);

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
    const cleanup = () => {
      setPlaying(false);
      URL.revokeObjectURL(url);
    };
    el.addEventListener('ended', cleanup);
    el.addEventListener('error', cleanup);
  }, [artifact.id, onGetPlaybackUrl, playing, audioEl]);

  const isPaused = artifact.state === 'paused';
  const isSaving = artifact.state === 'stopping';
  const isBusy =
    artifact.state === 'transcribing' || artifact.state === 'uploading';
  const isFailed = artifact.state === 'failed';
  const canPlay =
    !!onGetPlaybackUrl && artifact.size > 0 && !isSaving && !isBusy && !isPaused;

  return (
    <div
      className={`fi-audio-draft flex items-center gap-3 px-3 py-3 rounded-2xl bg-white/[0.06] border border-white/[0.12] backdrop-blur-sm ${className}`}
      role="group"
      aria-label="Audio grabado"
    >
      {/* Play / saving / busy / paused indicator */}
      <button
        type="button"
        onClick={handlePlay}
        disabled={!canPlay}
        aria-label={
          isPaused
            ? 'Grabación en pausa'
            : playing
            ? 'Pausar reproducción'
            : 'Reproducir grabación'
        }
        className="fi-audio-draft-play shrink-0 w-11 h-11 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95"
      >
        {isSaving || isBusy ? (
          <Loader2 className="w-5 h-5 animate-spin text-amber-400" />
        ) : isPaused ? (
          <CirclePause className="w-5 h-5 text-yellow-400" />
        ) : playing ? (
          <Pause className="w-5 h-5 text-white/90" />
        ) : (
          <Play className="w-5 h-5 text-white/90 ml-0.5" />
        )}
      </button>

      {/* Waveform bars + meta */}
      <div className="flex-1 min-w-0">
        <div className="flex items-end gap-[3px] h-8" aria-hidden="true">
          {BAR_HEIGHTS.map((h, i) => (
            <span
              key={i}
              className={`flex-1 rounded-full transition-colors duration-150 ${
                playing
                  ? 'bg-emerald-400/80'
                  : isPaused
                  ? 'bg-yellow-400/50'
                  : 'bg-white/40'
              }`}
              style={{ height: `${Math.round(h * 100)}%` }}
            />
          ))}
        </div>
        <div className="flex items-center gap-1.5 mt-1.5 text-xs text-white/50">
          <span className="tabular-nums">{formatArtifactDuration(artifact.durationMs)}</span>
          {artifact.size > 0 && (
            <>
              <span className="text-white/20">·</span>
              <span>{formatArtifactSize(artifact.size)}</span>
            </>
          )}
          {isPaused && <span className="text-yellow-400/70 font-medium">En pausa</span>}
          {isSaving && <span className="text-amber-400/70">Guardando…</span>}
          {isBusy && <span className="text-blue-400/70">Transcribiendo…</span>}
          {isFailed && artifact.errorMessage && (
            <span className="text-red-400/70 truncate">{artifact.errorMessage}</span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 shrink-0">
        {onDiscard && !isBusy && (
          <button
            type="button"
            onClick={() => onDiscard(artifact.id)}
            aria-label="Descartar grabación"
            className="fi-audio-draft-discard p-2 rounded-xl text-white/35 hover:text-red-400 hover:bg-white/10 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
        {onResume ? (
          <button
            type="button"
            onClick={onResume}
            aria-label="Reanudar grabación"
            className="fi-audio-draft-resume flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-300 transition-all active:scale-95"
          >
            <Play className="w-3.5 h-3.5 ml-0.5" />
            Reanudar
          </button>
        ) : isFailed && onRetry ? (
          <button
            type="button"
            onClick={() => onRetry(artifact.id)}
            aria-label="Reintentar"
            className="fi-audio-draft-retry p-2 rounded-xl text-amber-400/80 hover:text-amber-400 hover:bg-white/10 transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        ) : (
          onPrimary && (
            <button
              type="button"
              onClick={() => onPrimary(artifact.id)}
              disabled={isSaving || isBusy}
              className="fi-audio-draft-primary flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95"
            >
              <ArrowUp className="w-3.5 h-3.5" />
              {primaryActionLabel}
            </button>
          )
        )}
      </div>
    </div>
  );
}
