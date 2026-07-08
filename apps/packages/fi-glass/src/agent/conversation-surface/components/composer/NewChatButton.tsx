'use client';

/**
 * fi-glass · conversation-surface/NewChatButton — the built-in new-conversation
 * CTA rendered above the composer. Disabled while a turn streams; an app whose
 * chrome already owns the affordance opts out via `showNewChatButton` on the
 * surface (B3-OG118-5).
 */

export interface NewChatButtonProps {
  onClick: () => void;
  disabled: boolean;
  /** Button copy. Default: "New chat". */
  label?: string;
}

export function NewChatButton({ onClick, disabled, label = 'New chat' }: NewChatButtonProps) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '0.5rem' }}>
      <button
        onClick={onClick}
        disabled={disabled}
        style={{
          padding: '0.35rem 0.75rem',
          borderRadius: 8,
          border: '1px solid rgba(255,255,255,0.15)',
          background: 'transparent',
          color: '#94a3b8',
          fontSize: '0.8rem',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.5 : 1,
        }}
      >
        {label}
      </button>
    </div>
  );
}
