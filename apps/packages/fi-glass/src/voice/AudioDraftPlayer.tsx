'use client';

// B3-VOICE-FIGLASS-10 — Inline audio draft player.
// B3-VOICE-FIGLASS-17 — The draft plays through the SAME primitive as TTS.
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
//
// The og118 daily-driver audit (DD-VOICE-LOOP-COMPLETE) killed the home-grown
// mini-player: static decorative bars stretched edge-to-edge under the fluid
// column cap, the paused state showed a dead disabled pseudo-play button, and
// the duration read "--:--". Playback is now RichAudioPlayer — the exact
// primitive TTS uses (skip ±10s, scrubber, mm:ss readout).
//
// B3-VOICE-FIGLASS-18: the paused state plays back everything recorded so far.
// Segmented pause (useDurableRecording) yields a complete WAV at each pause,
// passed in as `pausedPreview`; while it is being spliced (or when the consumer
// doesn't provide one) the paused row falls back to the honest indicator
// (pulsing dot + recorded time + Resume) — never a dead play control.

import { useState, useEffect } from 'react';
import { Play, Trash2, Loader2, RotateCcw, ArrowUp } from 'lucide-react';
import type { AudioArtifact } from './audioArtifact';
import { formatArtifactDuration, formatArtifactSize } from './audioArtifact';
import { RichAudioPlayer } from './RichAudioPlayer';
import { FI_TOUCH_TARGET_CLASS, useTouchTargetStyle } from '../shell/touchTarget';

export interface AudioDraftPlayerProps {
  /** The draft artifact (the just-recorded, not-yet-acted-on audio). */
  artifact: AudioArtifact;
  /** Resolve a playback object URL for the artifact (revoked here on unmount). */
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
  /** Everything recorded so far, available while paused (segmented pause).
   * When set, the paused row plays it back through RichAudioPlayer. */
  pausedPreview?: Blob | null;
  /** Label for the primary action button (default: "Transcribir"). */
  primaryActionLabel?: string;
  /**
   * Visual chrome (COMPOSER-FRAME-2):
   *  - `"card"` (default): standalone frosted card — the sibling-card layout
   *    existing consumers render above the composer.
   *  - `"row"`: bare flex row for living INSIDE the composer box (the
   *    ComposerFrame header slot) — no background, border, radius or shadow;
   *    the box already provides the chrome.
   */
  variant?: 'card' | 'row';
  className?: string;
}

export function AudioDraftPlayer({
  artifact,
  onGetPlaybackUrl,
  onPrimary,
  onDiscard,
  onRetry,
  onResume,
  pausedPreview = null,
  primaryActionLabel = 'Transcribir',
  variant = 'card',
  className = '',
}: AudioDraftPlayerProps) {
  useTouchTargetStyle();
  const isPaused = artifact.state === 'paused';
  const isSaving = artifact.state === 'stopping';
  const isBusy =
    artifact.state === 'transcribing' || artifact.state === 'uploading';
  const isFailed = artifact.state === 'failed';
  const hasBlob = artifact.size > 0 && !isSaving && !isPaused;

  // Resolve the playback URL once per artifact and feed it to RichAudioPlayer
  // as its source; the object URL is revoked when the draft unmounts or the
  // artifact changes (the player engine releases its element on source swap).
  const [playbackUrl, setPlaybackUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!onGetPlaybackUrl || !hasBlob) {
      setPlaybackUrl(null);
      return;
    }
    let cancelled = false;
    let url: string | null = null;
    void onGetPlaybackUrl(artifact.id).then((resolved) => {
      if (cancelled) {
        if (resolved) URL.revokeObjectURL(resolved);
        return;
      }
      url = resolved;
      setPlaybackUrl(resolved);
    });
    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
      setPlaybackUrl(null);
    };
  }, [artifact.id, hasBlob, onGetPlaybackUrl]);

  return (
    <div
      className={
        variant === 'row'
          ? `fi-audio-draft fi-audio-draft--row flex items-center gap-3 px-2 py-1.5 ${className}`
          : `fi-audio-draft flex items-center gap-3 px-4 py-3 rounded-2xl bg-white/[0.07] border border-white/[0.14] backdrop-blur-xl shadow-lg shadow-black/30 ${className}`
      }
      role="group"
      aria-label="Audio grabado"
    >
      {isPaused && pausedPreview ? (
        // Paused with the recorded-so-far WAV in hand: play it back through
        // the SAME primitive the TTS player uses. The pulsing dot keeps
        // signalling that the recording session is still open.
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span
            className="fi-audio-draft-pauseddot shrink-0 w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse"
            aria-hidden="true"
          />
          <RichAudioPlayer
            source={pausedPreview}
            className="fi-audio-draft-player flex items-center gap-1 flex-1 min-w-0"
            buttonClassName="p-2 rounded-xl text-white/80 hover:text-white hover:bg-white/10 disabled:opacity-35 disabled:cursor-not-allowed transition-colors"
            iconClassName="w-4 h-4"
            progressClassName="flex-1 min-w-0 text-amber-400 cursor-pointer disabled:cursor-not-allowed"
          />
          <span className="hidden sm:inline text-xs font-medium text-amber-300/80 shrink-0">
            En pausa
          </span>
        </div>
      ) : isPaused ? (
        // Paused but the preview WAV is still being spliced (or the consumer
        // didn't wire one): honest status, never a dead play control.
        <div className="flex items-center gap-2.5 flex-1 min-w-0">
          <span
            className="fi-audio-draft-pauseddot shrink-0 w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse"
            aria-hidden="true"
          />
          <span className="text-sm tabular-nums text-white/80">
            {formatArtifactDuration(artifact.durationMs)}
          </span>
          <span className="text-xs font-medium text-amber-300/80">
            Grabación en pausa
          </span>
        </div>
      ) : (
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {/* Playback through the SAME primitive the TTS player uses. */}
          <RichAudioPlayer
            source={playbackUrl ? { url: playbackUrl } : null}
            className="fi-audio-draft-player flex items-center gap-1 flex-1 min-w-0"
            buttonClassName="p-2 rounded-xl text-white/80 hover:text-white hover:bg-white/10 disabled:opacity-35 disabled:cursor-not-allowed transition-colors"
            iconClassName="w-4 h-4"
            progressClassName="flex-1 min-w-0 text-emerald-400 cursor-pointer disabled:cursor-not-allowed"
          />
          <div className="hidden sm:flex items-center gap-1.5 shrink-0 text-xs text-white/45">
            {artifact.size > 0 && <span>{formatArtifactSize(artifact.size)}</span>}
            {isSaving && (
              <span className="inline-flex items-center gap-1 text-amber-400/70">
                <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden />
                Guardando…
              </span>
            )}
            {isBusy && <span className="text-blue-400/70">Transcribiendo…</span>}
          </div>
          {isFailed && artifact.errorMessage && (
            <span role="alert" className="text-xs text-red-400/80 truncate shrink min-w-0">
              {artifact.errorMessage}
            </span>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-1 shrink-0">
        {onDiscard && !isBusy && (
          <button
            type="button"
            onClick={() => onDiscard(artifact.id)}
            aria-label="Descartar grabación"
            className={`${FI_TOUCH_TARGET_CLASS} fi-audio-draft-discard p-2 rounded-xl text-white/35 hover:text-red-400 hover:bg-white/10 transition-colors`}
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
        {onResume ? (
          <button
            type="button"
            onClick={onResume}
            aria-label="Reanudar grabación"
            className={`${FI_TOUCH_TARGET_CLASS} fi-audio-draft-resume flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 transition-all active:scale-95`}
          >
            <Play className="w-3.5 h-3.5 ml-0.5" />
            Reanudar
          </button>
        ) : isFailed && onRetry ? (
          <button
            type="button"
            onClick={() => onRetry(artifact.id)}
            aria-label="Reintentar"
            className={`${FI_TOUCH_TARGET_CLASS} fi-audio-draft-retry p-2 rounded-xl text-amber-400/80 hover:text-amber-400 hover:bg-white/10 transition-colors`}
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        ) : (
          onPrimary && (
            <button
              type="button"
              onClick={() => onPrimary(artifact.id)}
              disabled={isSaving || isBusy}
              className={`${FI_TOUCH_TARGET_CLASS} fi-audio-draft-primary flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95`}
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
