'use client';

/**
 * fi-glass · SpeakButton — Californio (element 98), configurable optional.
 *
 * A trigger button that asks the app to open/play TTS for some text. The button
 * is pure presentation (lucide Volume2 + a click that calls onOpenPlayer); the
 * actual synthesis/playback is the app's job (it owns the AudioPlayer + its
 * VoiceAdapter). Extracted verbatim from aurity's chat/MessageActions SpeakButton,
 * with the aurity `Button` replaced by a plain <button> + className props — the
 * same move <CopyButton> made in Plutonio.
 *
 * CONFIGURABILITY (fire test): an app restyles via className/iconClassName, picks
 * the size preset, or relabels via `title`. Defaults reproduce aurity's icon-only
 * look. Drop it entirely by not rendering it.
 */

import { Volume2, Loader2 } from 'lucide-react';

export interface SpeakButtonProps {
  /** Text to speak. */
  content: string;
  /** Voice id (e.g. "nova"); shown in the tooltip. */
  voice?: string;
  /** Whether this is a user message (lets the player offer voice selection). */
  isUserMessage?: boolean;
  /** Open/play handler — provided by the app's audio player. */
  onOpenPlayer: (text: string, voice: string, isUserMessage?: boolean) => void;
  /**
   * Synthesis in flight (B3-VOICE-FIGLASS-6): renders a spinner instead of the
   * speaker, disables the button and sets aria-busy. TTS takes seconds; a
   * silent button reads as dead and invites paid spam clicks. Wire it to
   * `useVoice.isLoading` (scoped to this message via `currentText`).
   */
  busy?: boolean;
  /** Size preset (drives default padding + icon size). */
  size?: 'xs' | 'sm' | 'md';
  /** Override the button class entirely (e.g. aurity's exact legacy string). */
  className?: string;
  /** Override the icon class. */
  iconClassName?: string;
  /** Override the tooltip (default: "Escuchar (<voice>)"). */
  title?: string;
  /** Tooltip while busy (default: "Generando audio…"). */
  busyTitle?: string;
}

const ICON_SIZE = { xs: 'w-3 h-3', sm: 'w-3.5 h-3.5', md: 'w-4 h-4' } as const;
const PAD_SIZE = { xs: 'p-1', sm: 'p-1.5', md: 'p-2' } as const;

/** Pretty-print a voice id ("AvaNeural" → "Ava", "nova" → "Nova"). */
function formatVoiceName(voiceId: string): string {
  const match = voiceId.match(/([A-Z][a-z]+)Neural$/);
  if (match) return match[1];
  return voiceId.charAt(0).toUpperCase() + voiceId.slice(1);
}

export function SpeakButton({
  content,
  voice = 'nova',
  isUserMessage = false,
  onOpenPlayer,
  busy = false,
  size = 'sm',
  className,
  iconClassName,
  title,
  busyTitle = 'Generando audio…',
}: SpeakButtonProps) {
  const voiceDisplay = formatVoiceName(voice);
  const icon = iconClassName ?? ICON_SIZE[size];

  return (
    <button
      type="button"
      onClick={() => {
        if (!busy) onOpenPlayer(content, voice, isUserMessage);
      }}
      disabled={busy}
      aria-busy={busy}
      className={className ?? PAD_SIZE[size]}
      title={busy ? busyTitle : (title ?? `Escuchar (${voiceDisplay})`)}
      aria-label={busy ? busyTitle : `Escuchar mensaje con voz ${voiceDisplay}`}
    >
      {busy ? (
        <Loader2 className={`${icon} animate-spin`} />
      ) : (
        <Volume2 className={icon} />
      )}
    </button>
  );
}
