'use client';

/**
 * fi-glass · conversation-surface/TurnErrorBanner — recoverable turn-failure UI
 * (B3-FIGLASS-8). Rendered when the conversation carries a turnError (a
 * hung/timed-out or errored turn) INSTEAD of the zombie "thinking…" panel: the
 * watchdog/error already dropped the surface out of streaming. Style/copy hooks
 * are the consumer's; sensible defaults render without any.
 */

import type { PersistError, TurnError } from '../../../useAgentConversation';

export interface TurnErrorBannerProps {
  /** Any recoverable failure with a displayable message — a failed TURN, or a
   *  failed SAVE (PersistError). One banner anatomy, two callers. */
  error: TurnError | PersistError;
  onRetry: () => void;
  onDismiss: () => void;
  className?: string;
  /** Retry button copy. Default: "Reintentar". */
  retryLabel?: string;
  /** Dismiss button copy. Default: "Descartar". */
  dismissLabel?: string;
  retryButtonClassName?: string;
  dismissButtonClassName?: string;
}

export function TurnErrorBanner({
  error,
  onRetry,
  onDismiss,
  className,
  retryLabel = 'Reintentar',
  dismissLabel = 'Descartar',
  retryButtonClassName,
  dismissButtonClassName,
}: TurnErrorBannerProps) {
  return (
    <div
      role="alert"
      className={className}
      style={{
        marginTop: '1rem',
        padding: '0.75rem 1rem',
        borderRadius: 10,
        border: '1px solid rgba(248,113,113,0.35)',
        background: 'rgba(248,113,113,0.08)',
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: '0.75rem',
      }}
    >
      <span style={{ color: '#fca5a5', fontSize: '0.85rem', flex: 1, minWidth: 0 }}>
        {error.message}
      </span>
      <button
        type="button"
        onClick={onRetry}
        className={retryButtonClassName}
        style={
          retryButtonClassName
            ? undefined
            : {
                padding: '0.35rem 0.75rem',
                borderRadius: 8,
                border: '1px solid rgba(255,255,255,0.2)',
                background: 'transparent',
                color: '#e2e8f0',
                fontSize: '0.8rem',
                cursor: 'pointer',
              }
        }
      >
        {retryLabel}
      </button>
      <button
        type="button"
        onClick={onDismiss}
        className={dismissButtonClassName}
        style={
          dismissButtonClassName
            ? undefined
            : {
                padding: '0.35rem 0.75rem',
                borderRadius: 8,
                border: 'none',
                background: 'transparent',
                color: '#94a3b8',
                fontSize: '0.8rem',
                cursor: 'pointer',
              }
        }
      >
        {dismissLabel}
      </button>
    </div>
  );
}
