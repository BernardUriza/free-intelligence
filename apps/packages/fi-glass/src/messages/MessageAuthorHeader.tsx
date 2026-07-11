'use client';

/**
 * fi-glass · MessageAuthorHeader — the default "who said this" row: avatar token,
 * author name, time.
 *
 * The framework renders it AUTOMATICALLY for every bubble (TranscriptMessages),
 * off `ChatMessage.author` — a consumer does not opt in. og118 previously fed
 * the bubble a `renderHeader` that hardcoded the string "og118", so every answer
 * — including one produced by a selected element like Yodo — was attributed to
 * the app itself. Authorship is a property of the message, not of the consumer's
 * render slot, so the framework owns the row and the consumer owns only styling.
 *
 * `renderHeader` still exists as an ESCAPE HATCH (a shell that wants a different
 * anatomy), but the default is no longer "nothing".
 */

import type { ChatMessage, MessageAuthor } from '@free-intelligence/core';

export interface MessageAuthorHeaderProps {
  author: MessageAuthor;
  /** ISO timestamp; rendered as a short local time when parseable. */
  timestamp?: string;
  /** Drives the avatar palette (user vs assistant). */
  isUser?: boolean;
  /** BCP-47 locale for the time (defaults to the runtime's). */
  locale?: string;
}

const AVATAR = {
  width: 22,
  height: 22,
  borderRadius: 6,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 10,
  fontWeight: 600,
  flexShrink: 0,
} as const;

/** The avatar token: the author's symbol, else its first character. */
function avatarToken(author: MessageAuthor): string {
  const symbol = author.symbol?.trim();
  if (symbol) return symbol;
  return author.name.trim().slice(0, 2) || '?';
}

function formatTime(iso: string | undefined, locale?: string): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
}

export function MessageAuthorHeader({
  author,
  timestamp,
  isUser = false,
  locale,
}: MessageAuthorHeaderProps) {
  const time = formatTime(timestamp, locale);
  return (
    <>
      <span
        aria-hidden
        data-fi-author-avatar=""
        style={{
          ...AVATAR,
          background: isUser
            ? 'var(--fi-author-user-bg, rgba(124,58,237,0.8))'
            : 'var(--fi-author-agent-bg, var(--og-accent, #34d399))',
          color: isUser
            ? 'var(--fi-author-user-fg, #fff)'
            : 'var(--fi-author-agent-fg, #0a0f1e)',
        }}
      >
        {avatarToken(author)}
      </span>
      <span data-fi-author-name="" style={{ fontSize: 13, fontWeight: 500, color: '#cbd5e1' }}>
        {author.name}
      </span>
      {author.engine && (
        <span
          data-fi-author-engine=""
          style={{
            fontSize: 11,
            padding: '1px 6px',
            borderRadius: 9999,
            border: '1px solid rgba(255,255,255,0.12)',
            color: '#94a3b8',
          }}
        >
          {author.engine}
        </span>
      )}
      {time && (
        <span style={{ fontSize: 11, color: '#64748b', fontVariantNumeric: 'tabular-nums' }}>
          {time}
        </span>
      )}
    </>
  );
}

/**
 * The header for a stored message. A message written BEFORE authorship was part
 * of the contract carries none — it still gets attributed, from the side it sits
 * on: the agent's identity for an assistant bubble, the human's for a user one.
 * No bubble renders anonymous, ever.
 */
export function defaultMessageHeader(
  message: ChatMessage,
  agentAuthor: MessageAuthor,
  userAuthor: MessageAuthor,
  locale?: string,
) {
  const isUser = message.role === 'user';
  const author = message.author ?? (isUser ? userAuthor : agentAuthor);
  return (
    <MessageAuthorHeader
      author={author}
      timestamp={message.timestamp}
      isUser={isUser}
      locale={locale}
    />
  );
}
