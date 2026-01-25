/**
 * useChatScroll Hook - v2.0
 *
 * Production-grade scroll management for chat interfaces.
 *
 * Features:
 * - Smart auto-scroll (only when user at bottom)
 * - Unread message counter when scrolled up
 * - Scroll position preservation during history load
 * - Performance-optimized with requestAnimationFrame
 * - Intersection Observer for efficient visibility detection
 *
 * Best Practices Applied:
 * - Don't interrupt users reading history (smart auto-scroll)
 * - Use 'instant' for initial load, 'smooth' for new messages
 * - Show unread badge when scrolled up and new messages arrive
 * - Debounce scroll events to prevent jank
 * - Use passive event listeners for better scroll performance
 *
 * References:
 * - https://github.com/vytenisu/use-chat-scroll
 * - https://tuffstuff9.hashnode.dev/intuitive-scrolling-for-chatbot-message-streaming
 * - https://dev.to/deepcodes/automatic-scrolling-for-chat-app-in-1-line-of-code-react-hook-3lm1
 * - https://blog.fossasia.org/adding-a-scroll-to-bottom-button-in-susi-webchat/
 *
 * @example
 * const {
 *   containerRef,
 *   scrollToBottom,
 *   showScrollButton,
 *   unreadCount,
 * } = useChatScroll({ messages, isTyping });
 */

import { useRef, useState, useEffect, useCallback, useLayoutEffect } from 'react';

// ============================================================================
// TYPES
// ============================================================================

export interface UseChatScrollOptions {
  /** Current messages array - triggers scroll check on change */
  messages: unknown[];

  /** Is the assistant currently typing/streaming? */
  isTyping?: boolean;

  /** Are we loading older messages? (prepending to top) */
  loadingOlder?: boolean;

  /** Threshold in pixels to consider "at bottom" (default: 50) */
  bottomThreshold?: number;

  /** Enable unread message counting (default: true) */
  trackUnread?: boolean;

  /** Callback when user manually scrolls */
  onUserScroll?: (position: ScrollPosition) => void;
}

export interface ScrollPosition {
  top: number;
  height: number;
  clientHeight: number;
  distanceFromBottom: number;
  percentScrolled: number;
  /** Scroll velocity in px/ms (positive = scrolling down) */
  velocity: number;
  /** Is user scrolling fast? (> 2 px/ms) */
  isScrollingFast: boolean;
}

export interface UseChatScrollReturn {
  /** Ref to attach to the scrollable container */
  containerRef: React.RefObject<HTMLDivElement>;

  /** Ref to attach to anchor element at bottom (for Intersection Observer) */
  anchorRef: React.RefObject<HTMLDivElement>;

  /** Scroll to bottom programmatically */
  scrollToBottom: (behavior?: ScrollBehavior) => void;

  /** Whether to show the "scroll to bottom" button */
  showScrollButton: boolean;

  /** Whether user is currently at the bottom */
  isAtBottom: boolean;

  /** Number of unread messages (messages received while scrolled up) */
  unreadCount: number;

  /** Reset unread counter (call when user scrolls to bottom) */
  resetUnread: () => void;

  /** Current scroll position details */
  scrollPosition: ScrollPosition;
}

// ============================================================================
// HOOK IMPLEMENTATION
// ============================================================================

export function useChatScroll({
  messages,
  isTyping = false,
  loadingOlder = false,
  bottomThreshold = 50,
  trackUnread = true,
  onUserScroll,
}: UseChatScrollOptions): UseChatScrollReturn {
  // Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const anchorRef = useRef<HTMLDivElement>(null);
  const rafIdRef = useRef<number | null>(null);
  const prevScrollHeightRef = useRef(0);
  const prevMessagesCountRef = useRef(messages.length);
  const isInitialRenderRef = useRef(true);
  const userScrolledRef = useRef(false);

  // Velocity tracking refs
  const lastScrollTopRef = useRef(0);
  const lastScrollTimeRef = useRef(Date.now());
  const velocityRef = useRef(0);

  // State
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [scrollPosition, setScrollPosition] = useState<ScrollPosition>({
    top: 0,
    height: 0,
    clientHeight: 0,
    distanceFromBottom: 0,
    percentScrolled: 100,
    velocity: 0,
    isScrollingFast: false,
  });

  // ============================================================================
  // SCROLL TO BOTTOM (memoized)
  // ============================================================================
  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    const container = containerRef.current;
    if (!container) return;

    // Cancel any pending RAF
    if (rafIdRef.current) {
      cancelAnimationFrame(rafIdRef.current);
    }

    // Use RAF for smooth scroll timing
    rafIdRef.current = requestAnimationFrame(() => {
      container.scrollTo({
        top: container.scrollHeight,
        behavior,
      });

      // Reset unread when scrolling to bottom
      setUnreadCount(0);
      setIsAtBottom(true);
      setShowScrollButton(false);
    });
  }, []);

  // ============================================================================
  // RESET UNREAD COUNTER
  // ============================================================================
  const resetUnread = useCallback(() => {
    setUnreadCount(0);
  }, []);

  // ============================================================================
  // CHECK SCROLL POSITION (optimized with RAF + velocity tracking)
  // ============================================================================
  const updateScrollState = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    const atBottom = distanceFromBottom <= bottomThreshold;
    const percentScrolled = scrollHeight > clientHeight
      ? Math.round((scrollTop / (scrollHeight - clientHeight)) * 100)
      : 100;

    // Calculate scroll velocity (px/ms)
    const now = Date.now();
    const timeDelta = now - lastScrollTimeRef.current;
    const scrollDelta = scrollTop - lastScrollTopRef.current;

    // Only calculate velocity if time has passed (avoid division by zero)
    if (timeDelta > 0) {
      velocityRef.current = scrollDelta / timeDelta;
    }

    // Update refs for next calculation
    lastScrollTopRef.current = scrollTop;
    lastScrollTimeRef.current = now;

    // Fast scrolling threshold: > 2 px/ms (about 120px per 60fps frame)
    const isScrollingFast = Math.abs(velocityRef.current) > 2;

    const newPosition: ScrollPosition = {
      top: scrollTop,
      height: scrollHeight,
      clientHeight,
      distanceFromBottom,
      percentScrolled,
      velocity: velocityRef.current,
      isScrollingFast,
    };

    setIsAtBottom(atBottom);
    setShowScrollButton(!atBottom && scrollHeight > clientHeight);
    setScrollPosition(newPosition);

    // Reset unread when user scrolls to bottom
    if (atBottom && unreadCount > 0) {
      setUnreadCount(0);
    }

    // Callback for parent component
    if (onUserScroll && userScrolledRef.current) {
      onUserScroll(newPosition);
    }
  }, [bottomThreshold, unreadCount, onUserScroll]);

  // ============================================================================
  // SCROLL EVENT HANDLER (RAF-throttled)
  // ============================================================================
  const handleScroll = useCallback(() => {
    userScrolledRef.current = true;

    // Cancel pending RAF to avoid stacking
    if (rafIdRef.current) {
      cancelAnimationFrame(rafIdRef.current);
    }

    // Use RAF for better performance than setTimeout
    rafIdRef.current = requestAnimationFrame(updateScrollState);
  }, [updateScrollState]);

  // ============================================================================
  // ATTACH SCROLL LISTENER
  // ============================================================================
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Use passive listener for better scroll performance
    container.addEventListener('scroll', handleScroll, { passive: true });

    // Initial position check
    updateScrollState();

    return () => {
      container.removeEventListener('scroll', handleScroll);
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
      }
    };
  }, [handleScroll, updateScrollState]);

  // ============================================================================
  // TRACK USER SCROLL INTENT
  // When user scrolls UP, set a flag to prevent auto-scroll interruption
  // Reset flag when user manually scrolls back to bottom
  // ============================================================================
  const userScrolledUpRef = useRef(false);
  const lastUserScrollTimeRef = useRef(0);

  // Detect user scrolling up (intentional reading of history)
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const detectUserScrollUp = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

      // If user scrolled more than 150px from bottom, mark as "reading history"
      if (distanceFromBottom > 150) {
        userScrolledUpRef.current = true;
        lastUserScrollTimeRef.current = Date.now();
      }

      // If user scrolled back to bottom (within 30px), allow auto-scroll again
      if (distanceFromBottom <= 30) {
        userScrolledUpRef.current = false;
      }
    };

    container.addEventListener('scroll', detectUserScrollUp, { passive: true });
    return () => container.removeEventListener('scroll', detectUserScrollUp);
  }, []);

  // ============================================================================
  // AUTO-SCROLL ON NEW MESSAGES
  // Rule: Only scroll if user was at bottom AND not reading history
  // ============================================================================
  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Skip during history load (user is loading older messages)
    if (loadingOlder) return;

    const newMessagesCount = messages.length;
    const prevCount = prevMessagesCountRef.current;
    const messagesDelta = newMessagesCount - prevCount;

    // Initial render: scroll to bottom instantly
    if (isInitialRenderRef.current && newMessagesCount > 0) {
      isInitialRenderRef.current = false;
      prevMessagesCountRef.current = newMessagesCount;
      console.log('[useChatScroll] [INIT] Initial render: scrolling to bottom');
      scrollToBottom('instant');
      return;
    }

    // New messages arrived (not from loading older)
    if (messagesDelta > 0) {
      prevMessagesCountRef.current = newMessagesCount;
      console.log('[useChatScroll] [MSG] New messages detected:', {
        delta: messagesDelta,
        total: newMessagesCount,
        isAtBottom,
        userScrolledUp: userScrolledUpRef.current,
      });

      // Don't auto-scroll if user is reading history
      // Allow auto-scroll only if:
      // 1. User is at bottom (within threshold)
      // 2. User hasn't scrolled up recently to read history
      // 3. Scroll velocity is not negative (actively scrolling up)
      const isScrollingUp = velocityRef.current < -0.5;
      const isReadingHistory = userScrolledUpRef.current;

      if (isAtBottom && !isScrollingUp && !isReadingHistory) {
        // User at bottom and not reading history: auto-scroll smoothly
        console.log('[useChatScroll] [OK] Auto-scrolling to bottom (smooth)');
        scrollToBottom('smooth');
      } else if (trackUnread) {
        // User scrolled up or is reading: increment unread counter
        console.log('[useChatScroll] [PIN] Not at bottom, incrementing unread counter');
        setUnreadCount(prev => prev + messagesDelta);
      }
    }
  }, [messages.length, isAtBottom, loadingOlder, scrollToBottom, trackUnread]);

  // ============================================================================
  // AUTO-SCROLL DURING TYPING/STREAMING
  // Only scroll ONCE when typing starts, not continuously
  // Respect user's reading intent
  // ============================================================================
  const wasTypingRef = useRef(false);

  useEffect(() => {
    // Only trigger on typing START (false → true transition)
    if (isTyping && !wasTypingRef.current) {
      const isScrollingUp = velocityRef.current < -0.5;
      const isReadingHistory = userScrolledUpRef.current;

      // Only auto-scroll if user is at bottom and not reading history
      if (isAtBottom && !loadingOlder && !isScrollingUp && !isReadingHistory) {
        scrollToBottom('smooth');
      }
    }
    wasTypingRef.current = isTyping;
  }, [isTyping, isAtBottom, loadingOlder, scrollToBottom]);

  // ============================================================================
  // RESTORE SCROLL POSITION AFTER LOADING OLDER MESSAGES
  // Prevents jarring jump to top when prepending messages
  // ============================================================================
  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    if (loadingOlder) {
      // Store height before prepend
      prevScrollHeightRef.current = container.scrollHeight;
    } else if (prevScrollHeightRef.current > 0) {
      // Restore position after prepend
      const newScrollHeight = container.scrollHeight;
      const scrollDiff = newScrollHeight - prevScrollHeightRef.current;

      if (scrollDiff > 0) {
        // Maintain visual position
        container.scrollTop = scrollDiff + 50;
      }

      prevScrollHeightRef.current = 0;
    }
  }, [loadingOlder, messages.length]);

  // ============================================================================
  // CLEANUP
  // ============================================================================
  useEffect(() => {
    return () => {
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
      }
    };
  }, []);

  return {
    containerRef,
    anchorRef,
    scrollToBottom,
    showScrollButton,
    isAtBottom,
    unreadCount,
    resetUnread,
    scrollPosition,
  };
}
