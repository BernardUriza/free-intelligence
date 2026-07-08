'use client';

/**
 * fi-glass · conversation-surface/ComposerControls — the CONTENT of the
 * composer's footer slot: live dictation visualizer + mic slot + explicit send
 * button. Renders a fragment, no wrapper — ComposerFrame's footer slot owns the
 * row layout (flex, gap, alignment) via its injected stylesheet
 * (B3-FIGLASS-COMPOSER-FRAME-1). The orchestrator gates rendering (`footer`
 * stays null when no control applies) so the frame never mounts an empty row.
 *
 * micSlotOverride (B3-VOICE-OG118-6) replaces the built-in ComposerMicSlot +
 * dictation visualizer with custom content (e.g. a durable-recording button).
 */

import type { ReactNode } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { ComposerMicSlot, AudioVisualizer } from '../../../voice';
import { FI_TOUCH_TARGET_CLASS } from '../../../shell/touchTarget';
import type { SurfaceDictation } from '../hooks';

export interface ComposerControlsProps {
  dictation: SurfaceDictation;
  micSlotOverride?: ReactNode;
  micSlotClassName?: string;
  micButtonClassName?: string;
  voiceVisualizerClassName?: string;
  voiceVisualizerBarClassName?: string;
  showSendButton: boolean;
  canSend: boolean;
  isStreaming: boolean;
  onSend: () => void;
  /** aria-label for the send button. Default: "Enviar mensaje". */
  sendLabel?: string;
  sendButtonClassName?: string;
  sendButtonIconClassName?: string;
}

export function ComposerControls({
  dictation,
  micSlotOverride,
  micSlotClassName,
  micButtonClassName,
  voiceVisualizerClassName,
  voiceVisualizerBarClassName,
  showSendButton,
  canSend,
  isStreaming,
  onSend,
  sendLabel = 'Enviar mensaje',
  sendButtonClassName,
  sendButtonIconClassName,
}: ComposerControlsProps) {
  return (
    <>
      {/* Built-in dictation visualizer — suppressed when micSlotOverride is used.
          Live equalizer: reacts to the mic's frequency bands so the user sees
          they're being heard. Only mounted while recording, fed by the analyser
          the dictation hook already runs — no extra Web Audio here. */}
      {micSlotOverride == null && dictation.micAvailable && dictation.isRecording && (
        <AudioVisualizer
          levels={dictation.bands}
          active={dictation.isRecording}
          variant="bars"
          label="Nivel del micrófono"
          className={voiceVisualizerClassName}
          barClassName={voiceVisualizerBarClassName}
        />
      )}
      {/* micSlotOverride replaces the built-in ComposerMicSlot + dictation */}
      {micSlotOverride != null
        ? micSlotOverride
        : dictation.micAvailable && (
            <ComposerMicSlot
              available
              recording={dictation.isRecording}
              busy={dictation.isTranscribing}
              onStart={dictation.startDictation}
              onStop={dictation.stopDictation}
              className={micSlotClassName}
              buttonClassName={micButtonClassName}
            />
          )}
      {showSendButton && (
        // Explicit send affordance (mirrors the shell/AURITY composer). Enter
        // still sends; this is the visible button. Disabled until there's
        // trimmed text and nothing is streaming.
        <button
          type="button"
          onClick={onSend}
          disabled={!canSend}
          aria-label={sendLabel}
          className={
            sendButtonClassName
              ? `${FI_TOUCH_TARGET_CLASS} ${sendButtonClassName}`
              : FI_TOUCH_TARGET_CLASS
          }
        >
          {isStreaming ? (
            <Loader2
              className={
                sendButtonIconClassName
                  ? `${sendButtonIconClassName} animate-spin`
                  : 'animate-spin'
              }
              aria-hidden
            />
          ) : (
            <Send className={sendButtonIconClassName} aria-hidden />
          )}
        </button>
      )}
    </>
  );
}
