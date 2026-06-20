'use client';

/**
 * fi-glass · CopyButton — copy-to-clipboard action with check feedback.
 *
 * Pure primitive: Clipboard API + lucide icons. No app dependencies.
 *
 * CONFIGURABILITY (fire test): an app restyles via className props, relabels via
 * label props, handles failures via `onError`, or drops it entirely (just don't
 * render it) — all without touching fi-glass. Defaults reproduce aurity's exact
 * copy-button look and 2s reset.
 */

import { memo, useCallback, useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { messageStyles } from './styles';
import { FI_TOUCH_TARGET_CLASS, useTouchTargetStyle } from '../shell/touchTarget';

export interface CopyButtonProps {
  /** Text to copy to the clipboard. */
  content: string;
  /** Called if the Clipboard API rejects (default: silent). */
  onError?: (error: unknown) => void;
  /** Override the button base class. */
  className?: string;
  /** Override the idle-state class. */
  idleClassName?: string;
  /** Override the copied-state class. */
  activeClassName?: string;
  /** Override the icon class. */
  iconClassName?: string;
  /** Tooltip/label before copy (default: "Copiar"). */
  copyLabel?: string;
  /** Tooltip/label after copy (default: "Copiado"). */
  copiedLabel?: string;
  /** Milliseconds before the check resets to copy (default: 2000). */
  resetMs?: number;
}

export const CopyButton = memo(function CopyButton({
  content,
  onError,
  className,
  idleClassName,
  activeClassName,
  iconClassName,
  copyLabel = 'Copiar',
  copiedLabel = 'Copiado',
  resetMs = 2000,
}: CopyButtonProps) {
  const [copied, setCopied] = useState(false);
  useTouchTargetStyle();
  const { actions } = messageStyles;

  const base = className ?? actions.button.base;
  const idle = idleClassName ?? actions.button.idle;
  const active = activeClassName ?? actions.button.active;
  const icon = iconClassName ?? actions.icon;

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), resetMs);
    } catch (err) {
      onError?.(err);
    }
  }, [content, onError, resetMs]);

  return (
    <button
      onClick={handleCopy}
      className={`${FI_TOUCH_TARGET_CLASS} ${base} ${copied ? active : idle}`}
      title={copied ? copiedLabel : copyLabel}
      aria-label={copied ? copiedLabel : `${copyLabel} mensaje`}
    >
      {copied ? <Check className={icon} /> : <Copy className={icon} />}
    </button>
  );
});
