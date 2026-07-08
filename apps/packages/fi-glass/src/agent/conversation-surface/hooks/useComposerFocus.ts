'use client';

/**
 * fi-glass · conversation-surface/useComposerFocus — composer focus recovery
 * (B3-FIGLASS-10). The daily-driver audit's "Enter no envía": clicking the
 * mic/send button leaves focus ON the button, so the next Enter re-triggers the
 * button instead of sending. The surface owns the composer, so it owns getting
 * focus BACK to it after voice/send/stream — via the typed textarea ref (never
 * by reaching into the composer's internal DOM).
 *
 * Refocuses when a turn settles (clean finish, stream error, or the timeout
 * watchdog) and when dictation finishes transcribing — in both cases the user's
 * next natural act is typing/Enter, but their click left focus elsewhere.
 */

import { useCallback, useEffect, useRef, type RefObject } from 'react';

export function useComposerFocus(options: {
  isStreaming: boolean;
  isTranscribing: boolean;
}): RefObject<HTMLTextAreaElement | null> {
  const { isStreaming, isTranscribing } = options;
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const refocusComposer = useCallback(() => {
    const el = inputRef.current;
    if (!el || el.disabled) return;
    // Don't fight a user who focused another text-entry surface (e.g. an app's
    // token input). Stealing from buttons/body is the whole point — that's the
    // mic/send focus trap.
    const active = document.activeElement;
    const isOtherTextEntry =
      active instanceof HTMLElement &&
      active !== el &&
      (active.tagName === 'INPUT' ||
        active.tagName === 'TEXTAREA' ||
        active.isContentEditable);
    if (isOtherTextEntry) return;
    el.focus();
  }, []);

  // The textarea was disabled while streaming and focus was lost. A failed turn
  // refocuses too, so the user can edit/retry immediately.
  const wasStreaming = useRef(false);
  useEffect(() => {
    if (wasStreaming.current && !isStreaming) refocusComposer();
    wasStreaming.current = isStreaming;
  }, [isStreaming, refocusComposer]);

  const wasTranscribing = useRef(false);
  useEffect(() => {
    if (wasTranscribing.current && !isTranscribing) refocusComposer();
    wasTranscribing.current = isTranscribing;
  }, [isTranscribing, refocusComposer]);

  return inputRef;
}
