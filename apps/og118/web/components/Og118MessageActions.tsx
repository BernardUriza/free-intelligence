'use client';

/**
 * Og118MessageActions — per-message action toolbar for the transcript.
 *
 * Preserves the existing Copy action on every message and ADDS a Speak action on
 * assistant messages only (B3-TTS-1). Both buttons are fi-glass primitives:
 * CopyButton and SpeakButton are presentation-only — SpeakButton just fires
 * `onOpenPlayer`, and the app routes that to fi-glass `useVoice.generateAudio`.
 * No audio state lives here.
 *
 * Extracted as its own component so the wiring (Copy stays, Speak only on
 * assistant) is unit-testable without mounting the whole surface.
 */

import type { ChatMessage } from '@free-intelligence/core';
import { CopyButton } from 'fi-glass/messages';
import { SpeakButton } from 'fi-glass/voice';

export interface Og118MessageActionsProps {
  /** The transcript message this toolbar belongs to. */
  message: ChatMessage;
  /** Current voice id (from useVoice) — shown in the Speak tooltip. */
  currentVoice: string;
  /** Open/generate playback for `text` in `voice`. Wired to useVoice.generateAudio. */
  onSpeak: (text: string, voice: string, isUserMessage?: boolean) => void;
}

export function Og118MessageActions({ message, currentVoice, onSpeak }: Og118MessageActionsProps) {
  const isAssistant = message.role === 'assistant';
  return (
    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
      <CopyButton content={message.content} />
      {isAssistant && (
        <SpeakButton content={message.content} voice={currentVoice} onOpenPlayer={onSpeak} />
      )}
    </div>
  );
}
