'use client';

/**
 * Og118MessageMeta — the model badge for the transcript.
 *
 * The AUTHOR row (avatar + name + time) used to live here as a `renderHeader`
 * that hardcoded the strings "og118"/"o1", so every bubble claimed the app had
 * answered even when a selected element (Yodo, Oxígeno) actually did. Authorship
 * is a property of the message, not of a consumer render slot, so it moved into
 * the contract (`ChatMessage.author`) and fi-glass renders it automatically —
 * framework-first-canary: the canary's pain rose to the framework instead of
 * being patched in the wrapper. What stays here is genuinely app-specific: the
 * model-provenance chip, off `message.metadata.model`.
 */

import { Sparkles } from 'lucide-react';
import type { ChatMessage, MessageAuthor } from '@free-intelligence/core';

/** og118 itself — the speaker when no element is selected (base companion). */
export const OG118_AUTHOR: MessageAuthor = { id: 'og118', name: 'og118', symbol: 'og' };

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
