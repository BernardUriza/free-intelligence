'use client';

/**
 * ChatEmptyState Component
 *
 * Engaging empty state for chat widget showing welcome message and capabilities
 * Follows WCAG 2.1 accessibility guidelines
 */

import { MessageCircle, Check } from 'lucide-react';
import { emptyStateConfig, a11yLabels } from '@/config/chat-messages.config';

export interface ChatEmptyStateProps {
  /** User name for personalized greeting */
  userName?: string;
}

export function ChatEmptyState({ userName }: ChatEmptyStateProps) {
  return (
    <div className="chat-empty" role="status" aria-label={a11yLabels.emptyState}>
      <div className="chat-empty-container">
        <div className="chat-empty-icon" aria-hidden="true">
          <MessageCircle className="w-8 h-8" strokeWidth={1.5} />
        </div>
        <div className="fi-stack-md">
          <h3 className="chat-empty-title">{emptyStateConfig.welcomeTitle(userName)}</h3>
          <p className="chat-empty-subtitle">{emptyStateConfig.welcomeSubtitle}</p>
        </div>
        <ul className="chat-empty-features">
          {emptyStateConfig.features.map((feature, idx) => (
            <li key={idx} className="chat-empty-feature">
              <span className="chat-empty-feature-icon" aria-hidden="true">
                <Check className="w-4 h-4" strokeWidth={2} />
              </span>
              <span>{feature.text}</span>
            </li>
          ))}
        </ul>
        <p className="chat-empty-cta">{emptyStateConfig.ctaText}</p>
      </div>
    </div>
  );
}
