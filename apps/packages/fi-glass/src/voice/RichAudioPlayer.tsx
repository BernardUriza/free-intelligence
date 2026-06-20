'use client';

/**
 * fi-glass · RichAudioPlayer — full playback controls over `useAudioPlayer`.
 *
 * The minimal `<AudioPlayer>` (play/pause + stop) stays untouched for existing
 * consumers; this is the opt-in "rich" surface the og118 canary asked for:
 * skip-back / play-pause / stop / skip-forward, a draggable progress scrubber,
 * and a current-time / duration readout. It is pure presentation over the same
 * headless engine — no synthesis, no STT, no network. Apps still own the
 * VoiceAdapter and `useVoice`; this only PLAYS an already-resolved AudioSource.
 *
 * Accessibility: every control has a state-aware aria-label, the toggle exposes
 * aria-pressed, the scrubber is a native range input with aria-valuetext in
 * mm:ss, controls disable when there is nothing to play, and errors announce via
 * role="alert".
 */

import {
  Play,
  Pause,
  Square,
  Loader2,
  AlertCircle,
  RotateCcw,
  RotateCw,
} from 'lucide-react';
import type { AudioSource } from '@free-intelligence/core';
import { useEffect } from 'react';
import { useAudioPlayer } from './useAudioPlayer';
import { FI_TOUCH_TARGET_CLASS, useTouchTargetStyle } from '../shell/touchTarget';

export interface RichAudioPlayerProps {
  /** Audio to play; when it changes the player loads the new source. */
  source?: AudioSource | null;
  /** Start playing as soon as a new source loads. Default false. */
  autoPlay?: boolean;
  /** Seconds the skip-back / skip-forward controls jump. Default 10. */
  skipSeconds?: number;
  /** Show the mm:ss / mm:ss time readout. Default true. */
  showTime?: boolean;
  /** Called on a playback/load error. */
  onError?: (error: unknown, context: string) => void;
  /** Called when the clip finishes. */
  onEnded?: () => void;
  /** Override the wrapper class. */
  className?: string;
  /** Override the button class (applies to all transport buttons). */
  buttonClassName?: string;
  /** Override the icon class. */
  iconClassName?: string;
  /** Override the progress scrubber class. */
  progressClassName?: string;
}

const ICON = 'w-4 h-4';
const BTN = 'p-2 disabled:opacity-40';

/**
 * Format seconds as mm:ss (or h:mm:ss past an hour). Pure + exported so the
 * readout formatting is unit-tested without rendering. Guards NaN/negatives
 * (duration is NaN until metadata loads) by collapsing them to 0:00.
 */
export function formatPlaybackTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) seconds = 0;
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const ss = String(s).padStart(2, '0');
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${ss}`;
  return `${m}:${ss}`;
}

export function RichAudioPlayer({
  source,
  autoPlay = false,
  skipSeconds = 10,
  showTime = true,
  onError,
  onEnded,
  className,
  buttonClassName,
  iconClassName,
  progressClassName,
}: RichAudioPlayerProps) {
  const player = useAudioPlayer({ onError, onEnded });
  const {
    load,
    play,
    toggle,
    stop,
    seek,
    seekBy,
    isPlaying,
    isLoading,
    error,
    currentSrc,
    duration,
    currentTime,
  } = player;

  useEffect(() => {
    if (!source) return;
    load(source);
    if (autoPlay) void play();
    // play/load are stable controller methods; re-run only when the source changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source, autoPlay]);

  const hasSource = currentSrc !== null;
  const canSeek = hasSource && duration > 0;
  useTouchTargetStyle();
  const btnClass = `${FI_TOUCH_TARGET_CLASS} ${buttonClassName ?? BTN}`;
  const iconClass = iconClassName ?? ICON;
  const positionLabel = `${formatPlaybackTime(currentTime)} / ${formatPlaybackTime(
    duration
  )}`;

  return (
    <div
      className={className}
      data-fi-audio-player="rich"
      role="group"
      aria-label="Controles de reproducción de audio"
    >
      <button
        type="button"
        onClick={() => seekBy(-skipSeconds)}
        disabled={!canSeek}
        aria-label={`Retroceder ${skipSeconds} segundos`}
        className={btnClass}
      >
        <RotateCcw className={iconClass} aria-hidden />
      </button>

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

      <button
        type="button"
        onClick={() => seekBy(skipSeconds)}
        disabled={!canSeek}
        aria-label={`Avanzar ${skipSeconds} segundos`}
        className={btnClass}
      >
        <RotateCw className={iconClass} aria-hidden />
      </button>

      <input
        type="range"
        min={0}
        max={duration > 0 ? duration : 0}
        step={0.1}
        value={Math.min(currentTime, duration > 0 ? duration : currentTime)}
        onChange={(e) => seek(Number(e.target.value))}
        disabled={!canSeek}
        aria-label="Progreso de reproducción"
        aria-valuetext={positionLabel}
        className={progressClassName}
        data-fi-audio-progress=""
      />

      {showTime ? (
        <span data-fi-audio-time="" aria-hidden className="text-xs tabular-nums">
          {positionLabel}
        </span>
      ) : null}

      {error ? (
        <span role="alert" className="inline-flex items-center gap-1 text-xs">
          <AlertCircle className={iconClass} aria-hidden />
          Error de audio
        </span>
      ) : null}
    </div>
  );
}
