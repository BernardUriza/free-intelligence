'use client';

/**
 * ChatLegalDisclaimer Component
 *
 * Ephemeral legal disclaimer that auto-fades after configured time
 * Implements accessibility best practices (WCAG 2.1 Level AA)
 */

import { useEffect, useState } from 'react';
import { legalDisclaimerConfig, a11yLabels } from '@/config/chat-messages.config';

export interface ChatLegalDisclaimerProps {
  shouldShow: boolean;
}

export function ChatLegalDisclaimer({ shouldShow }: ChatLegalDisclaimerProps) {
  const [show, setShow] = useState(false);
  const [isFading, setIsFading] = useState(false);

  useEffect(() => {
    if (shouldShow) {
      setShow(true);
      setIsFading(false);

      const fadeTimer = setTimeout(() => setIsFading(true), legalDisclaimerConfig.timer.fadeStartMs);
      const hideTimer = setTimeout(() => setShow(false), legalDisclaimerConfig.timer.hideCompleteMs);

      return () => {
        clearTimeout(fadeTimer);
        clearTimeout(hideTimer);
      };
    }
  }, [shouldShow]);

  if (!show) return null;

  return (
    <div
      className={isFading ? 'chat-disclaimer-fading' : 'chat-disclaimer'}
      role="contentinfo"
      aria-label={a11yLabels.legalInfo}
      aria-live="polite"
    >
      <div className="chat-disclaimer-content">
        <div className="chat-disclaimer-inner">
          <div className="chat-disclaimer-header">
            <span className="text-base" aria-hidden="true">{legalDisclaimerConfig.emoji}</span>
            <p className="chat-disclaimer-title">{legalDisclaimerConfig.title}</p>
          </div>
          <p className="chat-disclaimer-text">{legalDisclaimerConfig.mainContent}</p>
          <p className="chat-disclaimer-footer">{legalDisclaimerConfig.footerNote}</p>
        </div>
      </div>
    </div>
  );
}
