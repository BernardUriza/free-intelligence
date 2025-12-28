/**
 * ChatWidget Responsive Integration Example
 *
 * Demonstrates mobile-first responsive design with useBreakpoints:
 * - Mobile (<640px): fullscreen overlay
 * - Tablet (640-1024px): modal at 90% viewport
 * - Desktop (>1024px): fixed widget at 384×600px
 */

import { useBreakpoints } from '@/hooks/useMediaQuery';
import { useState } from 'react';

/**
 * Mobile-first breakpoint definitions
 * Using .98px to avoid edge-case rounding issues
 */
const BREAKPOINTS = {
  mobile: '(max-width: 639.98px)',
  tablet: '(min-width: 640px) and (max-width: 1023.98px)',
  desktop: '(min-width: 1024px)',
};

export function ChatWidgetResponsive() {
  const { isMobile, isTablet, isDesktop: _isDesktop } = useBreakpoints(BREAKPOINTS, {
    // Return false on server to avoid hydration flash
    ssrMatch: false,
  });

  const [isOpen, setIsOpen] = useState(false);

  /**
   * Compute responsive styles based on breakpoint
   */
  const containerStyles = isMobile
    ? // Mobile: fullscreen takeover
      'fixed inset-0 z-50 h-screen w-screen bg-white'
    : isTablet
      ? // Tablet: modal dialog with backdrop
        'fixed bottom-4 right-4 z-50 w-[90vw] max-w-[900px] h-[90vh] rounded-2xl shadow-2xl bg-white'
      : // Desktop: fixed bottom-right widget
        'fixed bottom-6 right-6 z-50 w-[384px] h-[600px] rounded-2xl shadow-xl bg-white';

  /**
   * Mobile uses full-screen header, desktop uses compact title
   */
  const headerStyles = isMobile
    ? 'flex items-center justify-between px-4 py-3 border-b bg-blue-600 text-white'
    : 'flex items-center justify-between px-4 py-3 border-b bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-t-2xl';

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-40 w-14 h-14 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg flex items-center justify-center transition-transform hover:scale-110"
        aria-label="Open chat"
      >
        <svg
          className="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
          />
        </svg>
      </button>
    );
  }

  return (
    <>
      {/* Backdrop for tablet/mobile when modal is open */}
      {(isMobile || isTablet) && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Chat Widget Container */}
      <div className={containerStyles}>
        {/* Header */}
        <div className={headerStyles}>
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <h2 className="font-semibold">
              {isMobile ? 'Aurity Assistant' : 'Chat'}
            </h2>
          </div>

          <button
            onClick={() => setIsOpen(false)}
            className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
            aria-label="Close chat"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Example messages */}
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
              A
            </div>
            <div className="flex-1">
              <div className="bg-gray-100 rounded-2xl rounded-tl-none px-4 py-3">
                <p className="text-sm text-gray-900">
                  Hello! I&apos;m your Aurity assistant. How can I help you today?
                </p>
              </div>
              <p className="text-xs text-gray-500 mt-1 ml-1">2:34 PM</p>
            </div>
          </div>

          <div className="flex gap-3 justify-end">
            <div className="flex-1">
              <div className="bg-blue-600 text-white rounded-2xl rounded-tr-none px-4 py-3 ml-auto max-w-[80%]">
                <p className="text-sm">
                  I need help with my patient documentation.
                </p>
              </div>
              <p className="text-xs text-gray-500 mt-1 mr-1 text-right">
                2:35 PM
              </p>
            </div>
          </div>
        </div>

        {/* Input Area */}
        <div className="border-t p-4">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder={
                isMobile ? 'Type a message...' : 'Ask me anything...'
              }
              className="flex-1 px-4 py-2 border rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-full font-medium transition-colors"
              aria-label="Send message"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

/**
 * Alternative: Persistent widget with mode switching
 */
export function ChatWidgetPersistent() {
  const { isMobile, isTablet, isDesktop } = useBreakpoints(BREAKPOINTS);
  const [mode, _setMode] = useState<'normal' | 'expanded' | 'minimized'>(
    'normal'
  );

  // Mobile always fullscreen when expanded
  const isFullscreen = isMobile && mode === 'expanded';

  // Tablet uses modal behavior
  const isModal = isTablet && mode === 'expanded';

  // Desktop can be expanded to larger size
  const desktopExpanded = isDesktop && mode === 'expanded';

  const containerStyles = isFullscreen
    ? 'fixed inset-0 z-50'
    : isModal
      ? 'fixed bottom-4 right-4 z-50 w-[90vw] h-[90vh] rounded-2xl shadow-2xl'
      : desktopExpanded
        ? 'fixed bottom-6 right-6 z-50 w-[600px] h-[800px] rounded-2xl shadow-xl'
        : mode === 'minimized'
          ? 'fixed bottom-6 right-6 z-50 w-14 h-14'
          : 'fixed bottom-6 right-6 z-50 w-[384px] h-[600px] rounded-2xl shadow-xl';

  return <div className={containerStyles}>{/* Chat content */}</div>;
}

/**
 * Hook variant: custom breakpoint detection
 */
export function useResponsiveChatLayout() {
  const { isMobile, isTablet, isDesktop: _isDesktop } = useBreakpoints(BREAKPOINTS);

  return {
    layoutMode: isMobile ? 'fullscreen' : isTablet ? 'modal' : 'widget',
    shouldShowBackdrop: isMobile || isTablet,
    maxWidth: isMobile ? '100vw' : isTablet ? '90vw' : '384px',
    maxHeight: isMobile ? '100vh' : isTablet ? '90vh' : '600px',
    borderRadius: isMobile ? '0' : '1rem',
    position: isMobile ? 'fixed' : 'fixed',
    inset: isMobile ? '0' : undefined,
  };
}
