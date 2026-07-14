'use client';

/**
 * fi-glass · MessageBubble — generic message layout shell.
 *
 * Reproduces aurity's `<article>` message row EXACTLY, but every app-specific
 * region is a slot. The bubble owns ONLY structure + spacing; it knows nothing
 * about auth, personas, TTS, reasoning, or model badges.
 *
 * CONFIGURABILITY (fire test): turn off any region by passing nothing; change
 * any region's content by passing your own node. Nothing here needs editing to
 * reshape a message.
 *
 *   header   → avatar + author/meta row     (omit to hide)
 *   reasoning→ chain-of-thought block        (omit to hide)
 *   children → the message body              (required: e.g. <MessageContent/>)
 *   badge    → model/provenance chip          (omit to hide)
 *   actions  → hover toolbar (copy, TTS…)     (omit to hide)
 */

import { memo, useEffect, useRef, useState, type MouseEvent, type ReactNode } from 'react';
import { messageStyles } from './styles';
import { FI_MSG_ACTIONS_CLASS, useMessageActionsStyle } from './messageActionsStyle';

/** Broadcast channel for the touch actions-reveal: opening one bubble's actions
 * closes every other open bubble (one contextual toolbar at a time). */
const ACTIONS_OPEN_EVENT = 'fi-msg-actions-open';

export interface MessageBubbleProps {
  /** Drives alignment/background (user vs assistant). */
  role: 'user' | 'assistant';
  /** The message body (required). */
  children: ReactNode;
  /** Avatar + author/timestamp row. */
  header?: ReactNode;
  /** Reasoning / chain-of-thought block (rendered above the body). */
  reasoning?: ReactNode;
  /** Badge/chip rendered below the body (e.g. model, sources). */
  badge?: ReactNode;
  /** Hover action toolbar (e.g. copy, speak). */
  actions?: ReactNode;
  /** Marks the thread's last message: on touch its actions stay visible without
   * a tap (CONV-MOBILE-RECLAIM-1). */
  isLatest?: boolean;
  /** Extra classes appended to the article. */
  className?: string;
  /** Accessible label for the article. */
  ariaLabel?: string;
}

export const MessageBubble = memo(function MessageBubble({
  role,
  children,
  header,
  reasoning,
  badge,
  actions,
  isLatest = false,
  className,
  ariaLabel,
}: MessageBubbleProps) {
  useMessageActionsStyle();
  const { message: styles } = messageStyles;
  const isUser = role === 'user';
  // Touch reveal: tapping the row toggles its actions (messageActionsStyle
  // collapses them on coarse pointers). Interactive descendants keep their own
  // clicks — a link/button tap must never double as a toggle.
  const [actionsOpen, setActionsOpen] = useState(false);
  // Identity token for the mutual-exclusion broadcast (stable per instance).
  const selfToken = useRef({});
  useEffect(() => {
    if (!actionsOpen) return;
    const onOtherOpen = (e: Event) => {
      if ((e as CustomEvent).detail !== selfToken.current) setActionsOpen(false);
    };
    document.addEventListener(ACTIONS_OPEN_EVENT, onOtherOpen);
    return () => document.removeEventListener(ACTIONS_OPEN_EVENT, onOtherOpen);
  }, [actionsOpen]);
  const onBubbleClick = (e: MouseEvent<HTMLElement>) => {
    if (!actions) return;
    if ((e.target as HTMLElement).closest('a, button, input, textarea, [role="button"]')) return;
    const next = !actionsOpen;
    setActionsOpen(next);
    if (next) {
      document.dispatchEvent(
        new CustomEvent(ACTIONS_OPEN_EVENT, { detail: selfToken.current }),
      );
    }
  };

  return (
    <article
      // fi-msg-appear: 0.3s opacity fade-in on mount (B3-FIGLASS-12, ChatGPT
      // parity). Defined in theme/glass-chat.css — a consumer that doesn't
      // import it gets an instant appear (graceful no-op). Opacity only: a
      // transform here would suppress native CSS scroll anchoring.
      className={`fi-msg-appear ${styles.base} ${styles.borderRadius} ${isUser ? styles.user : styles.assistant} ${className || ''}`}
      role="article"
      aria-label={ariaLabel}
      data-fi-last-message={isLatest || undefined}
      data-fi-actions-open={actionsOpen || undefined}
      onClick={onBubbleClick}
    >
      {header && <div className="flex items-center gap-1.5 mb-0.5">{header}</div>}

      {reasoning && <div className="mt-3 mb-3">{reasoning}</div>}

      {children}

      {badge && <div className="mt-2">{badge}</div>}

      {actions != null && actions !== false && (
        <div className={FI_MSG_ACTIONS_CLASS}>{actions}</div>
      )}
    </article>
  );
});
