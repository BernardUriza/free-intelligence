'use client';

/* eslint-disable no-unused-vars */

/**
 * ChatWidgetContainer Component
 *
 * Container that handles different view modes with responsive breakpoints:
 * - normal: Floating widget (bottom-right)
 * - fullscreen: Takes entire viewport
 * - minimized: Compact bar
 * - expanded: Large modal view
 *
 * Responsive behavior:
 * - Mobile (<640px): Auto fullscreen when open
 * - Tablet (640-1024px): Modal at 90% viewport
 * - Desktop (>1024px): Fixed widget 384×600px
 */

import { MessageCircle } from 'lucide-react';
import type { ReactNode } from 'react';
import { useBreakpoints } from '@/hooks/useMediaQuery';
import { CHAT_BREAKPOINTS } from '@/config/chat.config';

export type ChatViewMode = 'normal' | 'fullscreen' | 'dense' | 'minimized' | 'expanded';

export interface ChatWidgetContainerProps {
  /** Current view mode */
  mode: ChatViewMode;

  /** Widget title (for minimized view) */
  title: string;

  /** Children (header, messages, input) */
  children: ReactNode;

  /** Whether the widget is embedded in a page (uses relative positioning) */
  embedded?: boolean;

  /** Callbacks */
  onModeChange: (mode: ChatViewMode) => void;
}

// eslint-disable-next-line no-unused-vars
export function ChatWidgetContainer(props: ChatWidgetContainerProps) {
  const { mode, title, children, embedded = false, onModeChange } = props;
  const { isMobile, isTablet } = useBreakpoints(CHAT_BREAKPOINTS, {
    ssrMatch: false,
  });

  // Compute effective mode based on breakpoint + user preference
  const effectiveMode: ChatViewMode =
    mode === 'minimized'
      ? 'minimized'
      : isMobile
        ? (mode === 'dense' ? 'dense' : 'fullscreen')
        : isTablet && (mode === 'normal' || mode === 'expanded')
          ? 'expanded'
          : mode;

  // MINIMIZED VIEW
  if (effectiveMode === 'minimized') {
    return (
      <div className="chat-container-minimized" onClick={() => onModeChange('normal')}>
        <MessageCircle className="chat-container-minimized-icon" />
        <span className="chat-container-minimized-title">{title}</span>
        <button
          onClick={(e) => { e.stopPropagation(); onModeChange('normal'); }}
          className="ml-2 fi-hover-ghost"
          aria-label="Expand chat"
        >
          <div className="chat-container-minimized-pulse" />
        </button>
      </div>
    );
  }

  // EXPANDED VIEW - Tablet modal
  if (effectiveMode === 'expanded' && isTablet) {
    return (
      <>
        <div className="chat-backdrop" onClick={() => onModeChange('normal')} />
        <div
          className="chat-container-expanded-tablet"
          style={{ width: 'min(90vw, 900px)', height: 'min(90vh, 800px)' }}
        >
          {children}
        </div>
      </>
    );
  }

  // EXPANDED VIEW - Desktop large widget
  if (effectiveMode === 'expanded') {
    return (
      <div
        className="chat-container-expanded"
        style={{
          width: 'min(80vw, 1200px)',
          height: '700px',
          maxWidth: 'calc(100vw - 3rem)',
          maxHeight: 'calc(100vh - 3rem)',
        }}
      >
        {children}
      </div>
    );
  }

  // EMBEDDED VIEW (inside AppTemplate)
  if (embedded && (effectiveMode === 'fullscreen' || effectiveMode === 'dense')) {
    return <div className="chat-container-embedded">{children}</div>;
  }

  // DENSE VIEW
  if (effectiveMode === 'dense') {
    return <div className="chat-container-dense">{children}</div>;
  }

  // FULLSCREEN VIEW
  if (effectiveMode === 'fullscreen') {
    return <div className="chat-container-fullscreen">{children}</div>;
  }

  // NORMAL VIEW (desktop floating widget)
  return <div className="chat-container-normal">{children}</div>;
}
