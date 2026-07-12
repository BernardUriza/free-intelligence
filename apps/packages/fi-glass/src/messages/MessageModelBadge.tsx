'use client';

/**
 * fi-glass · MessageModelBadge — the "powered by <model>" provenance chip.
 *
 * Rendered AUTOMATICALLY for any assistant message whose trace carries a model
 * (TranscriptMessages), like the author row. og118 owned a copy of this chip and
 * fed it `message.metadata.model` — a field NOTHING ever wrote (no consumer
 * emitted core's `meta` event, and persistence drops metadata anyway), so the
 * badge had never once rendered. The fix was upstream: the runner stamps the
 * model it actually used onto the result, the trace persists it, and the
 * framework renders it here. `renderBadge` remains the consumer's escape hatch.
 */

import type { ChatMessage } from '@free-intelligence/core';

export interface MessageModelBadgeProps {
  model: string;
  /** Copy for the tooltip; `{model}` is substituted. */
  title?: string;
  label?: string;
}

export function MessageModelBadge({
  model,
  title = 'Generado por {model}',
  label = 'Powered by',
}: MessageModelBadgeProps) {
  return (
    <span
      data-fi-model-badge=""
      title={title.replace('{model}', model)}
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
      {label}{' '}
      <span style={{ color: 'var(--fi-accent, var(--og-accent, #34d399))' }}>{model}</span>
    </span>
  );
}

/** The badge for a stored message; nothing when the turn recorded no model. */
export function defaultMessageBadge(message: ChatMessage) {
  if (message.role !== 'assistant') return undefined;
  const model = message.trace?.model?.trim();
  if (!model) return undefined;
  return <MessageModelBadge model={model} />;
}
