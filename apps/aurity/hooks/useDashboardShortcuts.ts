/**
 * useDashboardShortcuts - Keyboard shortcuts for dashboard operations
 *
 * Provides global keyboard shortcuts for common dashboard actions.
 * Shortcuts are disabled when user is typing in an input field.
 */

import { useEffect, useCallback, useRef } from 'react';
import { KEYBOARD_SHORTCUTS } from '@/lib/dashboard/constants';

interface UseDashboardShortcutsProps {
  /** Callback when "Call Next" shortcut is triggered (Ctrl+N) */
  onCallNext?: () => void;
  /** Callback when "Open TV" shortcut is triggered (Ctrl+T) */
  onOpenTV?: () => void;
  /** Callback when "Previous Slide" shortcut is triggered (←) */
  onPrevSlide?: () => void;
  /** Callback when "Next Slide" shortcut is triggered (→) */
  onNextSlide?: () => void;
  /** Callback when "Toggle Play" shortcut is triggered (Space) */
  onTogglePlay?: () => void;
  /** Callback when "Refresh" shortcut is triggered (Ctrl+R) */
  onRefresh?: () => void;
  /** Whether shortcuts are enabled (default: true) */
  enabled?: boolean;
}

/**
 * Check if the currently focused element is an input/textarea
 */
function isInputFocused(): boolean {
  const activeElement = document.activeElement;
  if (!activeElement) return false;

  const tagName = activeElement.tagName.toLowerCase();
  return (
    tagName === 'input' ||
    tagName === 'textarea' ||
    tagName === 'select' ||
    (activeElement as HTMLElement).isContentEditable
  );
}

export function useDashboardShortcuts({
  onCallNext,
  onOpenTV,
  onPrevSlide,
  onNextSlide,
  onTogglePlay,
  onRefresh,
  enabled = true,
}: UseDashboardShortcutsProps = {}) {
  // Track if shortcuts are currently active
  const isActive = useRef(enabled);
  isActive.current = enabled;

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Skip if shortcuts are disabled or user is typing
      if (!isActive.current || isInputFocused()) return;

      const { key, ctrlKey, metaKey } = event;
      const modifierPressed = ctrlKey || metaKey;

      // Ctrl+N: Call next patient
      if (
        modifierPressed &&
        key.toLowerCase() === KEYBOARD_SHORTCUTS.CALL_NEXT.key &&
        onCallNext
      ) {
        event.preventDefault();
        onCallNext();
        return;
      }

      // Ctrl+T: Open TV view
      if (
        modifierPressed &&
        key.toLowerCase() === KEYBOARD_SHORTCUTS.OPEN_TV.key &&
        onOpenTV
      ) {
        event.preventDefault();
        onOpenTV();
        return;
      }

      // Ctrl+R: Refresh data
      if (
        modifierPressed &&
        key.toLowerCase() === KEYBOARD_SHORTCUTS.REFRESH.key &&
        onRefresh
      ) {
        event.preventDefault();
        onRefresh();
        return;
      }

      // Arrow Left: Previous slide (no modifier needed)
      if (key === KEYBOARD_SHORTCUTS.PREV_SLIDE.key && onPrevSlide) {
        event.preventDefault();
        onPrevSlide();
        return;
      }

      // Arrow Right: Next slide (no modifier needed)
      if (key === KEYBOARD_SHORTCUTS.NEXT_SLIDE.key && onNextSlide) {
        event.preventDefault();
        onNextSlide();
        return;
      }

      // Space: Toggle auto-play (no modifier needed)
      if (key === KEYBOARD_SHORTCUTS.TOGGLE_PLAY.key && onTogglePlay) {
        event.preventDefault();
        onTogglePlay();
        return;
      }
    },
    [onCallNext, onOpenTV, onPrevSlide, onNextSlide, onTogglePlay, onRefresh]
  );

  useEffect(() => {
    if (!enabled) return;

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enabled, handleKeyDown]);

  // Return shortcut hints for UI display
  return {
    shortcuts: KEYBOARD_SHORTCUTS,
    isEnabled: enabled,
  };
}

/**
 * ShortcutHint component for displaying keyboard shortcut indicators
 */
export function formatShortcutKey(shortcut: { key: string; ctrlKey?: boolean }): string {
  const isMac = typeof navigator !== 'undefined' && navigator.platform.includes('Mac');
  const modifierKey = isMac ? '⌘' : 'Ctrl';

  if (shortcut.ctrlKey) {
    return `${modifierKey}+${shortcut.key.toUpperCase()}`;
  }

  // Format special keys
  switch (shortcut.key) {
    case 'ArrowLeft':
      return '←';
    case 'ArrowRight':
      return '→';
    case ' ':
      return 'Space';
    default:
      return shortcut.key.toUpperCase();
  }
}
