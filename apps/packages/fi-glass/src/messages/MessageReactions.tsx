'use client';

/**
 * fi-glass · MessageReactions — the emoji the speaker reacted to a turn with,
 * rendered as chips UNDER the bubble's text, the way Discord shows a reaction:
 * a gesture on the message, never a line inside it.
 *
 * Framework-owned so every shell renders a persona's reaction the same way the
 * moment its engine reports one (`ChatMessage.reactions`, from server-bot F5's
 * `OutboundTurn`). Before this, a reaction-only turn reached og118 as an empty
 * answer and a text turn's reaction was dropped — the persona's gesture had no
 * carrier on the web. Renders nothing when there are none, so the plain bubble
 * is byte-identical.
 */

import type { CSSProperties } from 'react';

export interface MessageReactionsProps {
  reactions: string[] | undefined;
  className?: string;
  chipClassName?: string;
  /** Accessible label for the row. Default: "Reacciones". */
  ariaLabel?: string;
}

const rowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '0.375rem',
  marginTop: '0.5rem',
};

const chipStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '0.125rem 0.5rem',
  borderRadius: '9999px',
  border: '1px solid var(--fi-reaction-border, rgba(127, 127, 127, 0.35))',
  background: 'var(--fi-reaction-bg, rgba(127, 127, 127, 0.12))',
  fontSize: '0.9375rem',
  lineHeight: 1.4,
};

export function MessageReactions({
  reactions,
  className,
  chipClassName,
  ariaLabel = 'Reacciones',
}: MessageReactionsProps) {
  const chips = (reactions ?? []).map((r) => r.trim()).filter(Boolean);
  if (chips.length === 0) return null;
  return (
    <div className={className} data-fi-message-reactions="" role="list" aria-label={ariaLabel} style={rowStyle}>
      {chips.map((emoji, i) => (
        <span key={`${emoji}-${i}`} role="listitem" className={chipClassName} style={chipStyle}>
          {emoji}
        </span>
      ))}
    </div>
  );
}
