'use client';

/**
 * ChatLoadingState Component
 *
 * Loading skeleton for initial chat load
 * Better contrast for accessibility (WCAG 2.1 Level AA)
 */

import { loadingStateConfig, a11yLabels } from '@/config/chat-messages.config';

export function ChatLoadingState() {
  return (
    <div className="chat-loading" role="status" aria-label={a11yLabels.loadingConversation}>
      <div className="chat-loading-container">
        <div className="chat-loading-skeleton">
          {loadingStateConfig.skeletonBars.map((bar, idx) => (
            <div key={idx} className="chat-loading-bar" style={{ width: bar.width }} />
          ))}
        </div>
        <p className="chat-loading-text">{loadingStateConfig.loadingText}</p>
      </div>
    </div>
  );
}

/**
 * LoadOlderMessagesIndicator Component
 *
 * Indicator shown at top of messages when loading older messages
 */
export interface LoadOlderMessagesIndicatorProps {
  /** Is currently loading older messages? */
  isLoading: boolean;
}

export function LoadOlderMessagesIndicator({ isLoading }: LoadOlderMessagesIndicatorProps) {
  if (!isLoading) return null;

  return (
    <div className="chat-loading-older" role="status" aria-label={a11yLabels.loadingOlderMessages}>
      <div className="chat-loading-older-content">
        <div className="chat-loading-spinner" aria-hidden="true" />
        <span>{loadingStateConfig.loadOlderText}</span>
      </div>
    </div>
  );
}
