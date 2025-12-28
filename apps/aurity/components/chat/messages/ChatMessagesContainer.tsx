'use client';

/**
 * ChatMessagesContainer - SOLID Composition Root
 *
 * This is the main container that composes all sub-components.
 * It follows SOLID principles:
 *
 * - S (Single Responsibility): Each sub-component has one job
 * - O (Open/Closed): Extensible via props without modifying internals
 * - L (Liskov): Sub-components are substitutable via composition
 * - I (Interface Segregation): Props split into focused interfaces
 * - D (Dependency Inversion): Depends on abstractions (hooks, configs)
 */

import { useCallback, useMemo } from 'react';
import type { FIMessage } from '@aurity-standalone/types/assistant';
import type { ChatConfig } from '@/config/chat.config';
import type { ChatViewMode } from '../ChatWidgetContainer';
import { useChatScroll } from '@/hooks/useChatScroll';
import { useChatKeyboardNav } from '@/hooks/useChatKeyboardNav';
import { spacing, a11yLabels } from '@/config/chat-messages.config';

// Sub-components (Single Responsibility)
import { LoadMoreButton } from './LoadMoreButton';
import { ScrollToBottomFAB } from './ScrollToBottomFAB';
import { Watermark } from './Watermark';
import { ScreenReaderAnnouncer } from './ScreenReaderAnnouncer';
import { ScrollSnapAnchor } from './ScrollSnapAnchor';
import { ChatMessagesContent } from './ChatMessagesContent';

// ============================================================================
// INTERFACE SEGREGATION: Split props into focused interfaces
// ============================================================================

/** Core message data */
export interface MessageDataProps {
  messages: FIMessage[];
  isTyping: boolean;
  loadingInitial?: boolean;
}

/** Pagination props */
export interface PaginationProps {
  onLoadOlder?: () => void;
  loadingOlder?: boolean;
  hasMoreMessages?: boolean;
}

/** Display configuration */
export interface DisplayProps {
  config: ChatConfig;
  mode?: ChatViewMode;
  userName?: string;
  containerId?: string;
  /** Currently selected persona (from selector) */
  selectedPersona?: string;
  streaming?: {
    status: 'idle' | 'streaming' | 'complete' | 'error';
    content: string;
    thinking: string;
    isStreaming: boolean;
  };
}

/** Combined props (composition) */
export interface ChatMessagesContainerProps
  extends MessageDataProps,
    PaginationProps,
    DisplayProps {}

// ============================================================================
// CONTAINER STYLES (centralized via CSS)
// ============================================================================

const getContainerClasses = (showWatermark: boolean, bgClass: string) =>
  `chat-messages-container ${showWatermark ? 'chat-messages-container-watermark' : ''} ${bgClass}`.trim();

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function ChatMessagesContainer({
  // Message data
  messages,
  isTyping,
  loadingInitial = false,
  // Pagination
  onLoadOlder,
  loadingOlder = false,
  hasMoreMessages = false,
  // Display
  config,
  mode = 'normal',
  userName,
  containerId = 'chat-widget-messages',
  selectedPersona,
  streaming,
}: ChatMessagesContainerProps) {
  // ============================================================================
  // DERIVED STATE
  // ============================================================================
  const showWatermark = mode === 'fullscreen';
  const containerClasses = getContainerClasses(showWatermark, config.theme.background.body);

  // ============================================================================
  // HOOKS (Dependency Inversion - abstractions)
  // ============================================================================
  const {
    containerRef,
    scrollToBottom,
    showScrollButton,
    unreadCount,
  } = useChatScroll({
    messages,
    isTyping,
    loadingOlder,
    trackUnread: true,
  });

  const { handleKeyDown } = useChatKeyboardNav({
    containerRef,
    scrollToBottom,
    onLoadMore: onLoadOlder,
    hasMore: hasMoreMessages,
  });

  // ============================================================================
  // CALLBACKS
  // ============================================================================
  const handleLoadMore = useCallback(() => {
    if (onLoadOlder && !loadingOlder && hasMoreMessages) {
      onLoadOlder();
    }
  }, [onLoadOlder, loadingOlder, hasMoreMessages]);

  const handleScrollToBottom = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      scrollToBottom('smooth');
    },
    [scrollToBottom]
  );

  // ============================================================================
  // SCREEN READER ANNOUNCEMENT
  // ============================================================================
  const announcement = useMemo(() => {
    if (messages.length === 0) return '';
    const lastMessage = messages[messages.length - 1];
    return lastMessage.role === 'user'
      ? a11yLabels.newMessageAnnouncement.user
      : a11yLabels.newMessageAnnouncement.assistant;
  }, [messages]);

  // ============================================================================
  // RENDER (Composition of single-responsibility components)
  // ============================================================================
  return (
    <div
      ref={containerRef}
      id={containerId}
      role="log"
      aria-label={a11yLabels.messagesContainer}
      aria-live="polite"
      aria-atomic="false"
      className={`${containerClasses} ${spacing.container.horizontal} ${spacing.container.top} ${spacing.container.bottom}`}
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      {/* A11y: Screen reader announcements */}
      <ScreenReaderAnnouncer announcement={announcement} />

      {/* Visual: Background watermark (ultra-sutil 2%) */}
      <Watermark visible={showWatermark} />

      {/* Pagination: Load more button */}
      {hasMoreMessages && (
        <LoadMoreButton
          onLoadMore={handleLoadMore}
          isLoading={loadingOlder}
        />
      )}

      {/* Content: Messages/Empty/Loading states */}
      <ChatMessagesContent
        messages={messages}
        isTyping={isTyping}
        loadingInitial={loadingInitial}
        config={config}
        userName={userName}
        selectedPersona={selectedPersona as any}
        showLegalDisclaimer={messages.length > 0}
        streaming={streaming}
      />

      {/* Spacing: Bottom padding */}
      <div className="chat-messages-bottom-spacer" aria-hidden="true" />

      {/* CSS: Scroll snap anchor */}
      <ScrollSnapAnchor />

      {/* Navigation: Scroll to bottom FAB */}
      <ScrollToBottomFAB
        onClick={handleScrollToBottom}
        unreadCount={unreadCount}
        visible={showScrollButton}
      />
    </div>
  );
}
