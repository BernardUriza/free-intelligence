'use client';

/**
 * fi-glass · conversation-surface/useComposerAppend — pull-once external text
 * injection (B3-VOICE-OG118-6, e.g. a durable-queue transcription). When
 * `composerAppend` becomes non-empty, append to the current input and signal
 * the consumer to reset it.
 */

import { useEffect, type Dispatch, type SetStateAction } from 'react';

export function useComposerAppend(options: {
  composerAppend: string | undefined;
  onComposerAppendConsumed: (() => void) | undefined;
  setInput: Dispatch<SetStateAction<string>>;
}): void {
  const { composerAppend, onComposerAppendConsumed, setInput } = options;
  // The dep array intentionally omits onComposerAppendConsumed/setInput to
  // avoid re-running on every parent render; both are stable in practice.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!composerAppend) return;
    setInput((prev) => (prev ? `${prev} ${composerAppend}` : composerAppend));
    onComposerAppendConsumed?.();
  }, [composerAppend]);
}
