'use client';

/**
 * fi-glass · ChatWidget — the chat shell orchestrator.
 *
 * Owns ONLY pure UI state (open/close, view mode via useChatWidgetState) and the
 * floating-button ↔ content switch. Every domain concern is inverted to props:
 * - auth        → `user` / `isAuthenticated` / `onLogin`
 * - conversation→ `chatHook` (REQUIRED; the app instantiates useFIConversation)
 * - config      → `config` (merged over the fi-glass neutral default)
 * - breakpoints → `isMobile` prop, else computed via fi-glass useMediaQuery
 * - persona / history / messages → slots the app fills
 * - input/voice/upload state → props (their hooks live in the app)
 *
 * fi-glass NEVER imports useAuth / useFIConversation / usePersonas / next/* /
 * @/components/ui/*.
 */

import { useCallback } from 'react';
import type { ChatMessage } from '@free-intelligence/core';
import { useChatWidgetState } from './useChatWidgetState';
import { useMediaQuery } from './useMediaQuery';
import { mergeChatConfig, CHAT_BREAKPOINTS } from './config';
import { FloatingButton } from './FloatingButton';
import { ChatContent } from './ChatContent';
import type { ChatWidgetProps } from './types';

export function ChatWidget<TMessage = ChatMessage, TNode = unknown>({
  chatHook,
  config: customConfig,
  user,
  isAuthenticated = false,
  onLogin,
  onNavigate,
  isMobile: isMobileProp,
  initialOpen = false,
  initialMode = 'normal',
  embedded = false,
  message,
  onMessageChange,
  onSend,
  responseMode,
  selectedPersona,
  personaName,
  showThinking,
  onResponseModeToggle,
  onShowThinkingToggle,
  onPersonaChange,
  onClearConversation,
  voiceState,
  onVoiceStart,
  onVoiceStop,
  uploadFile,
  uploadStatus,
  isUploadActive,
  onAttach,
  onCancelUpload,
  isStartingConversation = false,
  onStartConversation,
  personaSelector,
  renderHistory,
  renderMessages,
  onCopyCurl,
}: ChatWidgetProps<TMessage, TNode>) {
  // Breakpoint: prefer the injected value, else compute internally (pure).
  const internalIsMobile = useMediaQuery(CHAT_BREAKPOINTS.mobile, { ssrMatch: false });
  const isMobile = isMobileProp ?? internalIsMobile;

  // Merge app config over the fi-glass neutral default.
  const config = mergeChatConfig(customConfig);

  // Pure widget UI state (open/close, view mode, history panel).
  const widgetState = useChatWidgetState({ initialOpen, initialMode });

  // Read-only conversation state off the injected hook.
  const messages = chatHook.messages;
  const messageCount = messages.length;
  const loading = chatHook.loading;
  const isTyping = chatHook.isTyping;
  const loadingInitial = chatHook.loadingInitial ?? false;
  const customEmptyState = chatHook.customEmptyState as React.ReactNode;
  const customQuickReplies = chatHook.customQuickReplies as React.ReactNode;

  // Open the widget, marking the conversation started if there is history.
  const handleOpen = useCallback(() => {
    widgetState.open();
    widgetState.onMessagesLoaded(messageCount > 0);
  }, [widgetState, messageCount]);

  // Closed: floating button (hidden when embedded).
  if (!widgetState.isOpen) {
    if (embedded) return null;
    return <FloatingButton onClick={handleOpen} isMobile={isMobile} />;
  }

  // Open: the chat content shell.
  return (
    <ChatContent
      config={config}
      embedded={embedded}
      isAuthenticated={isAuthenticated}
      userName={user?.name || undefined}
      viewMode={widgetState.viewMode}
      isHistoryOpen={widgetState.isHistoryOpen}
      isStartingConversation={isStartingConversation}
      messageCount={messageCount}
      loading={loading}
      isTyping={isTyping}
      loadingInitial={loadingInitial}
      customEmptyState={customEmptyState}
      customQuickReplies={customQuickReplies}
      message={message}
      responseMode={responseMode}
      selectedPersona={selectedPersona}
      personaName={personaName}
      showThinking={showThinking}
      voiceState={voiceState}
      uploadFile={uploadFile}
      uploadStatus={uploadStatus}
      isUploadActive={isUploadActive}
      onNavigate={onNavigate}
      onModeChange={widgetState.setViewMode}
      onMinimize={widgetState.minimize}
      onMaximize={widgetState.maximize}
      onToggleDenseMode={widgetState.toggleDenseMode}
      onClose={widgetState.close}
      onHistoryOpen={widgetState.openHistory}
      onHistoryClose={widgetState.closeHistory}
      onStartConversation={onStartConversation ?? widgetState.startConversation}
      onLogin={onLogin ?? (() => {})}
      onMessageChange={onMessageChange}
      onSend={onSend}
      onResponseModeToggle={onResponseModeToggle}
      onShowThinkingToggle={onShowThinkingToggle}
      onPersonaChange={onPersonaChange}
      onClearConversation={onClearConversation}
      onVoiceStart={onVoiceStart}
      onVoiceStop={onVoiceStop}
      onAttach={onAttach}
      onCancelUpload={onCancelUpload}
      onCopyCurl={onCopyCurl}
      personaSelector={personaSelector}
      renderHistory={renderHistory}
      renderMessages={renderMessages}
    />
  );
}
