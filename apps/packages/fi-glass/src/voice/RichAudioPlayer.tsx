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
import { FI_TOUCH_QUERY } from '../theme/breakpoints';
import type { AudioSource } from '@free-intelligence/core';
import { useEffect } from 'react';
import type { CSSProperties } from 'react';
import { useAudioPlayer } from './useAudioPlayer';
import { FI_TOUCH_TARGET_CLASS, useTouchTargetStyle } from '../shell/touchTarget';

const SCRUBBER_STYLE_ID = 'fi-audio-scrubber-style';

/**
 * Injected idempotent stylesheet for the progress scrubber (same pattern as
 * `ensureTouchTargetStyle`). A bare `<input type="range">` renders with the
 * browser's native track + oversized thumb, which reads as foreign next to the
 * glass controls; `accent-color` only tints it, it never re-draws it. The
 * primitive owns the drawing: a 4px rounded track whose played portion fills
 * with `currentColor` (driven by the `--fi-audio-progress` custom property set
 * inline from playback state), so consumers pick the color with a plain text
 * class (`text-emerald-400`) instead of `accent-*`.
 */
function ensureAudioScrubberStyle(): void {
  if (typeof document === 'undefined') return;
  if (document.getElementById(SCRUBBER_STYLE_ID)) return;
  const el = document.createElement('style');
  el.id = SCRUBBER_STYLE_ID;
  el.textContent = `
    input[data-fi-audio-progress] {
      -webkit-appearance: none;
      appearance: none;
      height: 16px;
      margin: 0;
      padding: 0;
      background: transparent;
    }
    input[data-fi-audio-progress]::-webkit-slider-runnable-track {
      height: 4px;
      border-radius: 9999px;
      background: linear-gradient(
        to right,
        currentColor var(--fi-audio-progress, 0%),
        rgba(148, 163, 184, 0.3) var(--fi-audio-progress, 0%)
      );
    }
    input[data-fi-audio-progress]::-webkit-slider-thumb {
      -webkit-appearance: none;
      width: 12px;
      height: 12px;
      margin-top: -4px;
      border-radius: 9999px;
      background: currentColor;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.45);
    }
    input[data-fi-audio-progress]::-moz-range-track {
      height: 4px;
      border-radius: 9999px;
      background: rgba(148, 163, 184, 0.3);
    }
    input[data-fi-audio-progress]::-moz-range-progress {
      height: 4px;
      border-radius: 9999px;
      background: currentColor;
    }
    input[data-fi-audio-progress]::-moz-range-thumb {
      width: 12px;
      height: 12px;
      border: none;
      border-radius: 9999px;
      background: currentColor;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.45);
    }
    input[data-fi-audio-progress]:disabled {
      opacity: 0.35;
    }
    @media ${FI_TOUCH_QUERY} {
      input[data-fi-audio-progress] {
        height: var(--fi-touch-target, 44px);
      }
    }
  `;
  document.head.appendChild(el);
}

export interface RichAudioPlayerProps {
  /** Audio to play; when it changes the player loads the new source. */
  source?: AudioSource | null;
  /** Start playing as soon as a new source loads. Default false. */
  autoPlay?: boolean;
  /** Seconds the skip-back / skip-forward controls jump. Default 10. */
  skipSeconds?: number;
  /**
   * Compact transport for tight spaces (CONV-MOBILE-RECLAIM / voice-note preview
   * in the mobile composer). Drops the skip-back / stop / skip-forward buttons —
   * keeping only play-pause + scrubber + a SINGLE time readout — so the row fits
   * a phone-width composer beside a primary action (Transcribir / Guardar)
   * instead of pushing it off-screen. The full four-button transport (default)
   * stays for the standalone TTS player where the width is available.
   */
  compact?: boolean;
  /** Show the time readout. Default true. */
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
  compact = false,
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

  // Key the load effect on the source's VALUE, not its object identity: call
  // sites build `{ url }` inline, so every parent re-render yields a new object
  // while the audio is unchanged. Identity-keyed loading re-ran load() on each
  // render — resetting playback to 0 (and with autoPlay, restarting it) whenever
  // anything re-rendered the parent mid-playback. A Blob keys by reference
  // (parents hold it in state); a url source keys by its string.
  const sourceKey =
    source == null ? null : source instanceof Blob ? source : source.url;
  useEffect(() => {
    if (!source) return;
    load(source);
    if (autoPlay) void play();
    // play/load are stable controller methods; re-run only when the source
    // VALUE changes (sourceKey), never on parent-render object churn.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sourceKey, autoPlay]);

  const hasSource = currentSrc !== null;
  const canSeek = hasSource && duration > 0;
  useTouchTargetStyle();
  useEffect(() => {
    ensureAudioScrubberStyle();
  }, []);
  const progressPct =
    duration > 0 ? Math.min(100, (currentTime / duration) * 100) : 0;
  const btnClass = `${FI_TOUCH_TARGET_CLASS} ${buttonClassName ?? BTN}`;
  const iconClass = iconClassName ?? ICON;
  const positionLabel = `${formatPlaybackTime(currentTime)} / ${formatPlaybackTime(
    duration
  )}`;
  // Compact readout is a SINGLE value to save width in the mobile composer:
  // the current position once playback has moved (so pausing mid-clip keeps
  // showing where you are, not jumping to the clip length), else the clip
  // length at rest — never the dual "0:28 / 0:28" that crowds out the primary
  // action on a phone.
  const timeLabel = compact
    ? formatPlaybackTime(currentTime > 0 ? currentTime : duration)
    : positionLabel;

  return (
    <div
      className={className}
      data-fi-audio-player="rich"
      role="group"
      aria-label="Controles de reproducción de audio"
    >
      {!compact && (
        <button
          type="button"
          onClick={() => seekBy(-skipSeconds)}
          disabled={!canSeek}
          aria-label={`Retroceder ${skipSeconds} segundos`}
          className={btnClass}
        >
          <RotateCcw className={iconClass} aria-hidden />
        </button>
      )}

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

      {!compact && (
        <button
          type="button"
          onClick={stop}
          disabled={!hasSource}
          aria-label="Detener audio"
          className={btnClass}
        >
          <Square className={iconClass} aria-hidden />
        </button>
      )}

      {!compact && (
        <button
          type="button"
          onClick={() => seekBy(skipSeconds)}
          disabled={!canSeek}
          aria-label={`Avanzar ${skipSeconds} segundos`}
          className={btnClass}
        >
          <RotateCw className={iconClass} aria-hidden />
        </button>
      )}

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
        style={{ '--fi-audio-progress': `${progressPct}%` } as CSSProperties}
        data-fi-audio-progress=""
      />

      {showTime ? (
        <span
          data-fi-audio-time=""
          aria-hidden
          className="text-xs tabular-nums shrink-0"
        >
          {timeLabel}
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
