'use client';

/**
 * fi-glass · ComposerMicSlot — the reusable "place a mic here" primitive.
 *
 * The og118 canary surfaced a real gap: the composer has nowhere to host a
 * record button, and there is no STT adapter wired yet. The wrong fix is a
 * local mic in og118; the right one is a framework slot that renders the mic in
 * the correct visual states NOW and lights up later when a VoiceAdapter with
 * `transcribe` exists — without this component ever importing STT, a provider,
 * or the network.
 *
 * Contract: the slot is `available={false}` by default. While unavailable it
 * renders a clearly-disabled mic with an explanatory label (so the affordance
 * is discoverable but obviously not yet usable). When a consumer passes
 * `available` (i.e. it has an STT adapter), the slot becomes an enabled
 * record/stop toggle that delegates to the consumer's `onStart`/`onStop`; the
 * actual capture + transcription stay in the consumer, never here.
 *
 * Accessibility: the button always carries a state-aware aria-label, exposes
 * aria-pressed while recording, and sets disabled + aria-disabled when
 * unavailable or busy so it is skipped/announced correctly by assistive tech.
 */

import { Mic, MicOff, Square, Loader2 } from 'lucide-react';

export interface ComposerMicSlotProps {
  /**
   * Whether voice dictation is wired (an STT adapter exists). Default false →
   * the slot renders disabled/unavailable. No STT backend is required for the
   * slot itself; this flag is the consumer's declaration of capability.
   */
  available?: boolean;
  /** Currently capturing audio. */
  recording?: boolean;
  /** Transcribing / processing — shows a spinner and disables interaction. */
  busy?: boolean;
  /** Begin capture (consumer owns the recorder). Ignored when unavailable. */
  onStart?: () => void;
  /** Stop capture. Ignored when unavailable. */
  onStop?: () => void;
  /** Label/title shown while unavailable. */
  unavailableLabel?: string;
  /** aria-label for the start affordance. */
  startLabel?: string;
  /** aria-label for the stop affordance. */
  stopLabel?: string;
  /** aria-label while busy. */
  busyLabel?: string;
  /** Wrapper class. */
  className?: string;
  /** Button class. */
  buttonClassName?: string;
  /** Icon class. */
  iconClassName?: string;
}

const ICON = 'w-4 h-4';
const BTN = 'p-2 disabled:opacity-40';

export function ComposerMicSlot({
  available = false,
  recording = false,
  busy = false,
  onStart,
  onStop,
  unavailableLabel = 'Dictado por voz no disponible todavía',
  startLabel = 'Iniciar dictado por voz',
  stopLabel = 'Detener dictado por voz',
  busyLabel = 'Transcribiendo…',
  className,
  buttonClassName,
  iconClassName,
}: ComposerMicSlotProps) {
  const btnClass = buttonClassName ?? BTN;
  const iconClass = iconClassName ?? ICON;
  const disabled = !available || busy;

  const label = !available
    ? unavailableLabel
    : busy
      ? busyLabel
      : recording
        ? stopLabel
        : startLabel;

  const handleClick = () => {
    if (disabled) return;
    if (recording) onStop?.();
    else onStart?.();
  };

  const Icon = !available ? MicOff : busy ? Loader2 : recording ? Square : Mic;

  return (
    <div className={className} data-fi-mic-slot="" data-available={available ? '' : undefined}>
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled}
        aria-disabled={disabled}
        aria-pressed={available ? recording : undefined}
        aria-label={label}
        title={!available ? unavailableLabel : undefined}
        className={btnClass}
      >
        <Icon
          className={busy ? `${iconClass} animate-spin` : iconClass}
          aria-hidden
        />
      </button>
    </div>
  );
}
