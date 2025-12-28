'use client';

/**
 * MessageStatusIndicator - Shows message delivery status
 *
 * States: sending (spinner), sent (checkmark), failed (error + retry)
 * SOLID: Single responsibility - only displays status
 */

import { memo } from 'react';
import { CheckCheck, AlertCircle, Loader2, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { MessageStatus } from '@aurity-standalone/hooks/useOptimisticMessages';

export interface MessageStatusIndicatorProps {
  status: MessageStatus;
  error?: string;
  onRetry?: () => void;
  onDismiss?: () => void;
  showSentStatus?: boolean;
  size?: 'sm' | 'md';
}

export const MessageStatusIndicator = memo(function MessageStatusIndicator({
  status,
  error,
  onRetry,
  onDismiss,
  showSentStatus = false,
  size = 'sm',
}: MessageStatusIndicatorProps) {
  const iconSize = size === 'sm' ? 'w-3 h-3' : 'w-4 h-4';
  const textSize = size === 'sm' ? 'text-xs' : 'text-sm';

  if (status === 'sending') {
    return (
      <div className={`chat-status-sending ${textSize}`}>
        <Loader2 className={`${iconSize} animate-spin`} />
        <span className="opacity-70">Enviando...</span>
      </div>
    );
  }

  if (status === 'failed') {
    return (
      <div className="flex flex-col gap-1">
        <div className={`chat-status-failed ${textSize}`}>
          <AlertCircle className={iconSize} />
          <span>{error || 'Error al enviar'}</span>
        </div>
        <div className="fi-flex-gap">
          {onRetry && (
            <Button onClick={onRetry} className={`chat-status-retry ${textSize}`} aria-label="Reintentar envío" variant="danger" size="sm" type="button" icon={RotateCcw}>
              Reintentar
            </Button>
          )}
          {onDismiss && (
            <Button onClick={onDismiss} className={`chat-status-dismiss ${textSize}`} aria-label="Descartar mensaje" variant="ghost" size="sm" type="button">
              Descartar
            </Button>
          )}
        </div>
      </div>
    );
  }

  if (status === 'sent' && showSentStatus) {
    return (
      <div className={`chat-status-sent ${textSize}`}>
        <CheckCheck className={iconSize} />
      </div>
    );
  }

  return null;
});
