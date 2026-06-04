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

import { memo, type ReactNode } from 'react';
import { messageStyles } from './styles';

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
  className,
  ariaLabel,
}: MessageBubbleProps) {
  const { message: styles } = messageStyles;
  const isUser = role === 'user';

  return (
    <article
      className={`${styles.base} ${styles.borderRadius} ${isUser ? styles.user : styles.assistant} ${className || ''}`}
      role="article"
      aria-label={ariaLabel}
    >
      {header && <div className="flex items-center gap-2 mb-1">{header}</div>}

      {reasoning && <div className="mt-3 mb-3">{reasoning}</div>}

      {children}

      {badge && <div className="mt-2">{badge}</div>}

      {actions}
    </article>
  );
});
