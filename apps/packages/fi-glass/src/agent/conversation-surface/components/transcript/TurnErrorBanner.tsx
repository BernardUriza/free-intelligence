'use client';

/**
 * fi-glass · conversation-surface/TurnErrorBanner — recoverable turn-failure UI
 * (B3-FIGLASS-8). Rendered when the conversation carries a turnError (a
 * hung/timed-out or errored turn) INSTEAD of the zombie "thinking…" panel: the
 * watchdog/error already dropped the surface out of streaming. Style/copy hooks
 * are the consumer's; sensible defaults render without any.
 *
 * The same anatomy carries a waiting NOTICE (`tone="info"`, no retry): a turn
 * the engine released without its answer (OG118-EXTERNAL-TURN-1) is not a
 * failure, so it reads as status, never as an alert.
 */

import { useTouchTargetStyle, withTouchTarget } from '../../../../shell/touchTarget';

export interface TurnErrorBannerProps {
  /** Any recoverable failure with a displayable message: a failed turn, save or
   *  sidebar action. One banner anatomy for every caller. */
  error: { message: string };
  /** Absent for a notice: there is nothing to retry. */
  onRetry?: () => void;
  onDismiss: () => void;
  /** `error` (default) is an alert in red; `info` is a status in blue. */
  tone?: 'error' | 'info';
  className?: string;
  /** Retry button copy. Default: "Reintentar". */
  retryLabel?: string;
  /** Dismiss button copy. Default: "Descartar". */
  dismissLabel?: string;
  retryButtonClassName?: string;
  dismissButtonClassName?: string;
}

const TONES = {
  error: { border: 'rgba(248,113,113,0.35)', background: 'rgba(248,113,113,0.08)', text: '#fca5a5' },
  info: { border: 'rgba(96,165,250,0.35)', background: 'rgba(96,165,250,0.08)', text: '#93c5fd' },
} as const;

const BUTTON_STYLE = {
  padding: '0.35rem 0.75rem',
  borderRadius: 8,
  border: '1px solid rgba(255,255,255,0.2)',
  background: 'transparent',
  color: '#e2e8f0',
  fontSize: '0.8rem',
  cursor: 'pointer',
} as const;

export function TurnErrorBanner({
  error,
  onRetry,
  onDismiss,
  tone = 'error',
  className,
  retryLabel = 'Reintentar',
  dismissLabel = 'Descartar',
  retryButtonClassName,
  dismissButtonClassName,
}: TurnErrorBannerProps) {
  useTouchTargetStyle();
  const colors = TONES[tone];
  return (
    <div
      role={tone === 'info' ? 'status' : 'alert'}
      className={className}
      style={{
        marginTop: '1rem',
        padding: '0.75rem 1rem',
        borderRadius: 10,
        border: `1px solid ${colors.border}`,
        background: colors.background,
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: '0.75rem',
      }}
    >
      <span style={{ color: colors.text, fontSize: '0.85rem', flex: 1, minWidth: 0 }}>
        {error.message}
      </span>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className={withTouchTarget(retryButtonClassName)}
          style={retryButtonClassName ? undefined : BUTTON_STYLE}
        >
          {retryLabel}
        </button>
      )}
      <button
        type="button"
        onClick={onDismiss}
        className={withTouchTarget(dismissButtonClassName)}
        style={dismissButtonClassName ? undefined : { ...BUTTON_STYLE, opacity: 0.7 }}
      >
        {dismissLabel}
      </button>
    </div>
  );
}
