/**
 * fi-glass · useChatWidgetState — widget UI state (open/close, view mode,
 * history panel, conversation-started). Pure React, no domain. Copied verbatim
 * from aurity (it had zero coupling).
 */

import { useState, useCallback } from 'react';
import type { ChatViewMode } from 'fi-glass/shell';

export interface UseChatWidgetStateOptions {
  initialOpen: boolean;
  initialMode: ChatViewMode;
}

export interface UseChatWidgetStateReturn {
  isOpen: boolean;
  viewMode: ChatViewMode;
  isHistoryOpen: boolean;
  conversationStarted: boolean;
  isStartingConversation: boolean;
  open: () => void;
  close: () => void;
  setViewMode: (mode: ChatViewMode) => void;
  minimize: () => void;
  maximize: () => void;
  toggleDenseMode: () => void;
  openHistory: () => void;
  closeHistory: () => void;
  startConversation: () => void;
  onMessagesLoaded: (hasMessages: boolean) => void;
}

export function useChatWidgetState({
  initialOpen,
  initialMode,
}: UseChatWidgetStateOptions): UseChatWidgetStateReturn {
  const [isOpen, setIsOpen] = useState(initialOpen);
  const [viewMode, setViewMode] = useState<ChatViewMode>(initialMode);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [conversationStarted, setConversationStarted] = useState(false);
  const [isStartingConversation, _setIsStartingConversation] = useState(false);

  const open = useCallback(() => {
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    setViewMode('normal'); // Reset to normal for next open
  }, []);

  const minimize = useCallback(() => {
    if (viewMode === 'expanded') {
      setViewMode('normal');
    }
    // For dense mode, we handle toggle separately in toggleDenseMode
  }, [viewMode]);

  const maximize = useCallback(() => {
    setViewMode(viewMode === 'expanded' ? 'normal' : 'expanded');
  }, [viewMode]);

  const toggleDenseMode = useCallback(() => {
    setViewMode(viewMode === 'dense' ? 'fullscreen' : 'dense');
  }, [viewMode]);

  const openHistory = useCallback(() => {
    setIsHistoryOpen(true);
  }, []);

  const closeHistory = useCallback(() => {
    setIsHistoryOpen(false);
  }, []);

  const startConversation = useCallback(() => {
    setConversationStarted(true);
  }, []);

  const onMessagesLoaded = useCallback((hasMessages: boolean) => {
    if (hasMessages) {
      setConversationStarted(true);
    }
  }, []);

  return {
    isOpen,
    viewMode,
    isHistoryOpen,
    conversationStarted,
    isStartingConversation,
    open,
    close,
    setViewMode,
    minimize,
    maximize,
    toggleDenseMode,
    openHistory,
    closeHistory,
    startConversation,
    onMessagesLoaded,
  };
}
