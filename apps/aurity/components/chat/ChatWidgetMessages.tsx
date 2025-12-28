'use client';

/**
 * ChatWidgetMessages Component - SOLID Architecture (v3.0)
 *
 * This file now serves as a facade/re-export for the SOLID-refactored
 * ChatMessagesContainer component. This maintains backward compatibility
 * while the internal implementation follows SOLID principles.
 *
 * SOLID Implementation:
 * - S (Single Responsibility): Each sub-component in ./messages/ has one job
 * - O (Open/Closed): Extensible via props without modifying internals
 * - L (Liskov): Sub-components are substitutable via composition
 * - I (Interface Segregation): Props split into MessageDataProps, PaginationProps, DisplayProps
 * - D (Dependency Inversion): Components depend on hooks/configs, not concrete implementations
 *
 * Sub-components:
 * - LoadMoreButton: Pagination trigger
 * - ScrollToBottomFAB: Navigation button with unread badge
 * - Watermark: Background branding
 * - ScreenReaderAnnouncer: A11y announcements
 * - ScrollSnapAnchor: CSS scroll-snap target
 * - ChatMessagesContent: Content state rendering
 *
 * Hooks:
 * - useChatScroll: Scroll management (auto-scroll, velocity, unread count)
 * - useChatKeyboardNav: Keyboard navigation (End, Home, PageUp, PageDown)
 *
 * References:
 * - SOLID Principles: https://www.digitalocean.com/community/conceptual-articles/s-o-l-i-d-the-first-five-principles-of-object-oriented-design
 * - React Composition: https://react.dev/learn/thinking-in-react
 * - WCAG 2.1 Guidelines
 */

// Re-export the SOLID container as the main component
export {
  ChatMessagesContainer as ChatWidgetMessages,
  type ChatMessagesContainerProps as ChatWidgetMessagesProps,
} from './messages/ChatMessagesContainer';

// Also export sub-components for advanced usage
export {
  LoadMoreButton,
  ScrollToBottomFAB,
  Watermark,
  ScreenReaderAnnouncer,
  ScrollSnapAnchor,
  ChatMessagesContent,
} from './messages';
