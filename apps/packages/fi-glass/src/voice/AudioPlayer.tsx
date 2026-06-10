'use client';

/**
 * fi-glass · AudioPlayer — minimal, accessible playback controls for TTS audio.
 *
 * Presentation over `useAudioPlayer`: a play/pause toggle, a stop button, and
 * visible loading/error state. Self-contained — pass an `AudioSource` and it
 * loads it (and revokes the object URL on unmount via the hook). Pure styling
 * hooks (className overrides) like SpeakButton/CopyButton; drop it by not
 * rendering it. The app still owns synthesis (useVoice) and the VoiceAdapter.
 *
 * Accessibility: the toggle exposes aria-pressed + a state-aware aria-label, the
 * stop button is disabled when there is nothing to stop, and the error is
 * announced via role="alert".
 */

import { Play, Pause, Square, Loader2, AlertCircle } from 'lucide-react';
import type { AudioSource } from '@free-intelligence/core';
import { useEffect } from 'react';
import { useAudioPlayer } from './useAudioPlayer';

export interface AudioPlayerProps {
  /** Audio to play; when it changes the player loads the new source. */
  source?: AudioSource | null;
  /** Start playing as soon as a new source loads. Default false. */
  autoPlay?: boolean;
  /** Called on a playback/load error. */
  onError?: (error: unknown, context: string) => void;
  /** Called when the clip finishes. */
  onEnded?: () => void;
  /** Override the wrapper class. */
  className?: string;
  /** Override the button class (applies to both buttons). */
  buttonClassName?: string;
  /** Override the icon class. */
  iconClassName?: string;
}

const ICON = 'w-4 h-4';
const BTN = 'p-2 disabled:opacity-40';

export function AudioPlayer({
  source,
  autoPlay = false,
  onError,
  onEnded,
  className,
  buttonClassName,
  iconClassName,
}: AudioPlayerProps) {
  const player = useAudioPlayer({ onError, onEnded });
  const { load, play, toggle, stop, isPlaying, isLoading, error, currentSrc } =
    player;

  useEffect(() => {
    if (!source) return;
    load(source);
    if (autoPlay) void play();
    // play/load are stable controller methods; re-run only when the source changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source, autoPlay]);

  const hasSource = currentSrc !== null;
  const btnClass = buttonClassName ?? BTN;
  const iconClass = iconClassName ?? ICON;

  return (
    <div className={className} data-fi-audio-player="">
      <button
        type="button"
        onClick={() => void toggle()}
        disabled={!hasSource || isLoading}
        aria-pressed={isPlaying}
        aria-label={isPlaying ? 'Pausar audio' : 'Reproducir audio'}
        className={btnClass}
      >
        {isLoading ? (
          <Loader2 className={`${iconClass} animate-spin`} aria-hidden />
        ) : isPlaying ? (
          <Pause className={iconClass} aria-hidden />
        ) : (
          <Play className={iconClass} aria-hidden />
        )}
      </button>

      <button
        type="button"
        onClick={stop}
        disabled={!hasSource}
        aria-label="Detener audio"
        className={btnClass}
      >
        <Square className={iconClass} aria-hidden />
      </button>

      {error ? (
        <span role="alert" className="inline-flex items-center gap-1 text-xs">
          <AlertCircle className={iconClass} aria-hidden />
          Error de audio
        </span>
      ) : null}
    </div>
  );
}
