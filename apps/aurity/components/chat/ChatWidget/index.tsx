"use client";

/**
 * ChatWidget - Floating Chat with Free Intelligence
 *
 * Refactored into SOLID modules:
 * - types.ts: Type definitions
 * - useChatWidgetState.ts: Widget UI state (open/close, view mode)
 * - useChatPreferences.ts: User preferences (persona, response mode)
 * - useVoiceInput.ts: Voice recording integration
 * - useFileUploadState.ts: File upload integration
 * - FloatingButton.tsx: Floating button component
 * - ChatContent.tsx: Main chat content component
 *
 * Architecture:
 *   ChatWidget → useChat → assistantAPI → /assistant/chat
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { useBreakpoints } from '@/hooks/useMediaQuery';
import { useFIConversation } from '@aurity-standalone/hooks/useFIConversation';
import { defaultChatConfig, type ChatConfig, CHAT_BREAKPOINTS } from '@/config/chat.config';

import type { ChatWidgetProps } from './types';
import { useChatWidgetState } from './useChatWidgetState';
import { useChatPreferences } from './useChatPreferences';
import { useVoiceInput } from './useVoiceInput';
import { useFileUploadState } from './useFileUploadState';
import { FloatingButton } from './FloatingButton';
import { ChatContent } from './ChatContent';

export type { ChatWidgetProps };

export function ChatWidget({
  config: customConfig,
  initialOpen = false,
  initialMode = 'normal',
  embedded = false,
  chatHook,
}: ChatWidgetProps = {}) {
  const { user, isAuthenticated, loginWithRedirect } = useAuth();
  const { isMobile } = useBreakpoints(CHAT_BREAKPOINTS);
  const [message, setMessage] = useState('');

  // Merge config with defaults
  const config: ChatConfig = {
    ...defaultChatConfig,
    ...customConfig,
    theme: { ...defaultChatConfig.theme, ...customConfig?.theme },
    behavior: { ...defaultChatConfig.behavior, ...customConfig?.behavior },
    timestamp: { ...defaultChatConfig.timestamp, ...customConfig?.timestamp },
    animation: { ...defaultChatConfig.animation, ...customConfig?.animation },
  };

  // Widget UI state
  const widgetState = useChatWidgetState({
    initialOpen,
    initialMode,
  });

  // User preferences
  const preferences = useChatPreferences();

  // Storage key for authenticated users
  const storageKey = user?.sub ? `fi_chat_widget_${user.sub}` : undefined;

  // Memoize context to ensure it updates when selectedPersona or responseMode changes
  const chatContext = useMemo(() => {
    // Ensure persona is a string id (preferences.selectedPersona may be null)
    const personaId = typeof preferences.selectedPersona === 'string' && preferences.selectedPersona
      ? preferences.selectedPersona
      : 'general_assistant';
    return {
      doctor_id: user?.sub,
      doctor_name: user?.name,
      persona: personaId,
      response_mode: preferences.responseMode, // concise vs explanatory
    };
  }, [user?.sub, user?.name, preferences.selectedPersona, preferences.responseMode]);

  // Default chat hook
  const defaultChatHook = useFIConversation({
    phase: undefined,
    context: chatContext,
    storageKey,
    autoIntroduction: false,
    responseMode: preferences.responseMode, // Response style from user preferences
  });

  // Use injected hook or default
  const {
    messages,
    loading,
    isTyping,
    loadingInitial = false,
    sendMessage: _sendMessage,
    sendMessageStream,        // ← Streaming function
    streaming,                 // ← Streaming state
    loadOlderMessages = async () => {},
    hasMoreMessages = false,
    loadingOlder = false,
    clearConversation,
    streamingMessage: _streamingMessage,
    customEmptyState,
    customQuickReplies,
  } = chatHook || defaultChatHook;

  // Voice input
  const voiceInput = useVoiceInput({
    userId: user?.sub || 'anonymous',
    message,
    setMessage,
  });

  // File upload
  const fileUpload = useFileUploadState({
    persona: preferences.selectedPersona || 'assistant',
    userId: user?.sub || undefined,
  });

  // Handle open with messages check
  const handleOpen = useCallback(() => {
    widgetState.open();
    widgetState.onMessagesLoaded(messages.length > 0);
  }, [widgetState, messages.length]);

  // Handle send
  const handleSend = useCallback(async () => {
    if (!message.trim() || loading) return;
    const userMessage = message.trim();
    setMessage('');
    if (sendMessageStream) {
      await sendMessageStream(userMessage);  // ← Use streaming
    }
  }, [message, loading, sendMessageStream]);

  // Handle login
  const handleLogin = useCallback(() => {
    loginWithRedirect({
      appState: { returnTo: window.location.pathname },
    });
  }, [loginWithRedirect]);

  // Listen for memory clear events
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'chat_messages' && e.newValue === null) {
        clearConversation?.();
        setMessage('');
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [clearConversation]);

  // Render floating button when closed
  if (!widgetState.isOpen) {
    if (embedded) return null;
    return <FloatingButton onClick={handleOpen} isMobile={isMobile} />;
  }

  // Render chat content when open
  return (
    <ChatContent
      config={config}
      embedded={embedded}
      isAuthenticated={isAuthenticated}
      userName={user?.name || undefined}
      viewMode={widgetState.viewMode}
      isHistoryOpen={widgetState.isHistoryOpen}
      conversationStarted={widgetState.conversationStarted}
      isStartingConversation={widgetState.isStartingConversation}
      messages={messages}
      loading={loading}
      isTyping={isTyping}
      loadingInitial={loadingInitial}
      hasMoreMessages={hasMoreMessages}
      loadingOlder={loadingOlder}
      customEmptyState={customEmptyState}
      customQuickReplies={customQuickReplies}
      message={message}
      responseMode={preferences.responseMode}
      selectedPersona={preferences.selectedPersona || 'assistant'}
      voiceState={voiceInput.voiceState}
      uploadFile={fileUpload.file}
      uploadStatus={fileUpload.status}
      isUploadActive={fileUpload.isActive}
      streaming={streaming && {
        status: streaming.status === 'thinking' ? 'streaming' : (streaming.status as 'idle' | 'streaming' | 'complete' | 'error'),
        content: streaming.content,
        thinking: streaming.thinking,
        isStreaming: streaming.isStreaming,
      }}
      onModeChange={widgetState.setViewMode}
      onMinimize={widgetState.minimize}
      onMaximize={widgetState.maximize}
      onToggleDenseMode={widgetState.toggleDenseMode}
      onClose={widgetState.close}
      onHistoryOpen={widgetState.openHistory}
      onHistoryClose={widgetState.closeHistory}
      onStartConversation={widgetState.startConversation}
      onLogin={handleLogin}
      onLoadOlder={loadOlderMessages}
      onMessageChange={setMessage}
      onSend={handleSend}
      showThinking={preferences.showThinking}
      onShowThinkingToggle={preferences.toggleShowThinking}
      onResponseModeToggle={preferences.toggleResponseMode}
      onPersonaChange={preferences.setPersona}
      onVoiceStart={voiceInput.startVoice}
      onVoiceStop={voiceInput.stopVoice}
      onAttach={fileUpload.openPicker}
      onCancelUpload={fileUpload.cancel}
      onClearConversation={clearConversation}
    />
  );
}
