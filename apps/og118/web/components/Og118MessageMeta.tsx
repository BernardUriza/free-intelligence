'use client';

/**
 * Og118MessageMeta — header (avatar + author + time) and model badge for the
 * transcript, filling the MessageBubble slots og118 left empty.
 *
 * Pure app-specific wiring (framework-first-canary: branding/copy/identity
 * belong to the consumer): the slots (`header`, `badge`) and their layout have
 * lived in fi-glass MessageBubble since Plutonio; og118 simply never passed
 * renderHeader/renderBadge. The badge's model provenance comes from
 * `message.metadata.model`, persisted by core's foldAssistantTurn.
 */

import { Sparkles } from 'lucide-react';
import type { ChatMessage } from '@free-intelligence/core';

const AVATAR_BASE: React.CSSProperties = {
  width: 22,
  height: 22,
  borderRadius: 6,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 10,
  fontWeight: 600,
  flexShrink: 0,
};

/** "14:32" in the user's locale; empty for unparseable/missing timestamps. */
function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
}

export function Og118MessageHeader({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  const time = formatTime(message.timestamp);
  return (
    <>
      <span
        aria-hidden
        style={{
          ...AVATAR_BASE,
          background: isUser ? 'rgba(124,58,237,0.8)' : 'var(--og-accent, #34d399)',
          color: isUser ? '#fff' : '#0a0f1e',
        }}
      >
        {isUser ? 'Tú' : 'o1'}
      </span>
      <span style={{ fontSize: 13, fontWeight: 500, color: '#cbd5e1' }}>
        {isUser ? 'Tú' : 'og118'}
      </span>
      {time && (
        <span
          style={{ fontSize: 11, color: '#64748b', fontVariantNumeric: 'tabular-nums' }}
        >
          {time}
        </span>
      )}
    </>
  );
}

/** "Powered by <model>" chip — assistant messages with persisted provenance only. */
export function Og118ModelBadge({ message }: { message: ChatMessage }) {
  if (message.role !== 'assistant') return null;
  const model = message.metadata?.model;
  if (typeof model !== 'string' || model.trim() === '') return null;
  return (
    <span
      title={`Generado por ${model}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        padding: '2px 8px',
        borderRadius: 9999,
        border: '1px solid rgba(255,255,255,0.1)',
        background: 'rgba(15,23,42,0.5)',
        fontSize: 11,
        color: '#94a3b8',
      }}
    >
      <Sparkles size={11} style={{ color: 'var(--og-accent, #34d399)' }} aria-hidden />
      Powered by <span style={{ color: 'var(--og-accent, #34d399)' }}>{model}</span>
    </span>
  );
}
