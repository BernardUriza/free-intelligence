'use client';

/**
 * fi-glass · ChatContent — the open-widget shell skeleton.
 *
 * Composes the container + header + (start/empty/messages) + input + toolbar.
 * Domain pieces arrive as slots: `personaSelector` (into the toolbar),
 * `renderHistory` and `renderMessages` (the app's HistorySearch /
 * ChatWidgetMessages). `usePersonas` is gone — the selected persona's display
 * name comes in as `personaName`. The input uses fi-glass's own Composer.
 */

import { Loader2 } from 'lucide-react';
import { Composer } from 'fi-glass/composer';
import { ChatWidgetContainer } from './ChatWidgetContainer';
import { ChatWidgetHeader } from './ChatWidgetHeader';
import { ChatToolbar } from './ChatToolbar';
import { ChatFilePreview } from 'fi-glass/shell';
import { ChatStartScreen } from './ChatStartScreen';
import type { ChatContentProps } from './types';

export function ChatContent({
  config,
  embedded,
  isAuthenticated,
  userName,
  viewMode,
  isHistoryOpen,
  isStartingConversation,
  messageCount,
  loading,
  isTyping,
  loadingInitial,
  customEmptyState,
  customQuickReplies,
  message,
  responseMode,
  selectedPersona,
  personaName,
  showThinking = true,
  voiceState,
  uploadFile,
  uploadStatus,
  isUploadActive,
  uploadPrompt,
  onNavigate,
  onModeChange,
  onMinimize,
  onMaximize,
  onToggleDenseMode,
  onClose,
  onHistoryOpen,
  onHistoryClose,
  onStartConversation,
  onLogin,
  onMessageChange,
  onSend,
  onResponseModeToggle,
  onShowThinkingToggle,
  onPersonaChange: _onPersonaChange,
  onClearConversation,
  onVoiceStart,
  onVoiceStop,
  onAttach,
  onCancelUpload,
  onCopyCurl,
  personaSelector,
  renderHistory,
  renderMessages,
}: ChatContentProps) {
  // Dynamic placeholder like ChatGPT: "Escribe a [Persona Name]". Falls back to
  // a neutral prompt when the app has no personas (personaName omitted).
  const dynamicPlaceholder = personaName
    ? `Escribe a ${personaName}...`
    : 'Escribe tu mensaje...';

  // Feature-off by absence: a control is shown only when its handler is wired.
  // An app that omits voice/upload/persona/response-mode (e.g. og118 hello-chat)
  // gets a clean toolbar instead of dead buttons. aurity wires all → unchanged.
  const showVoice = typeof onVoiceStart === 'function';
  const showAttach = typeof onAttach === 'function';
  const showResponseMode = typeof onResponseModeToggle === 'function';
  const showThinkingToggle = typeof onShowThinkingToggle === 'function';
  const showClear = typeof onClearConversation === 'function';
  const showPersonaSelector = personaSelector != null;

  return (
    <div className="relative flex h-full flex-1 flex-col overflow-hidden">
        {/* Main Chat Window */}
        {!isHistoryOpen && (
          <ChatWidgetContainer
            mode={viewMode}
            title={config.title}
            embedded={embedded}
            onModeChange={onModeChange}
          >
            {/* Show header only in non-dense modes AND when not embedded (embedded uses AppTemplate header) */}
            {viewMode !== 'dense' && !embedded && (
              <ChatWidgetHeader
                title={config.title}
                subtitle={config.subtitle}
                backgroundClass={config.theme.background.header}
                mode={viewMode}
                showControls={!embedded}
                onNavigate={onNavigate}
                onMinimize={onMinimize}
                onMaximize={onMaximize}
                onToggleDenseMode={onToggleDenseMode}
                onClose={onClose}
                onHistorySearch={onHistoryOpen}
              />
            )}

            {messageCount === 0 && loadingInitial ? (
              <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
              </div>
            ) : messageCount === 0 && !isTyping && customEmptyState ? (
              customEmptyState
            ) : messageCount === 0 && !isTyping ? (
              <ChatStartScreen
                isAuthenticated={isAuthenticated}
                userName={userName}
                onStart={onStartConversation}
                onLogin={onLogin}
                onNavigate={onNavigate}
                isLoading={isStartingConversation}
              />
            ) : (
              renderMessages?.({ viewMode })
            )}

            {customQuickReplies}

            {/* Show toolbar and input only in non-dense modes */}
            {viewMode !== 'dense' && (
              <div className="chat-input-wrapper">
                <div className="chat-input-floating-box">
                  {/* File upload preview */}
                  {isUploadActive && uploadFile && (
                    <ChatFilePreview
                      file={uploadFile}
                      status={uploadStatus ?? 'selecting'}
                      onCancel={onCancelUpload ?? (() => {})}
                    />
                  )}

                  {/* The staged step: how should the persona USE this document?
                      Answering it is what starts the indexing. */}
                  {isUploadActive && uploadPrompt}

                  {/* Input ARRIBA - solo textarea */}
                  <Composer
                    message={message}
                    loading={loading}
                    placeholder={dynamicPlaceholder}
                    onMessageChange={onMessageChange}
                    onSend={onSend}
                    maxRows={5}
                    areaClassName="chat-input-area-top"
                    wrapperClassName="flex-1"
                    textareaClassName="chat-textarea"
                  />

                  {/* Toolbar ABAJO - con botones + mic + send */}
                  <ChatToolbar
                    responseMode={responseMode}
                    selectedPersona={selectedPersona}
                    showThinking={showThinking}
                    voiceRecording={voiceState}
                    personaSelector={personaSelector}
                    showAttach={showAttach}
                    showLanguage={false}
                    showFormatting={false}
                    showResponseMode={showResponseMode}
                    showVoice={showVoice}
                    showPersonaSelector={showPersonaSelector}
                    showThinkingToggle={showThinkingToggle}
                    showClear={showClear}
                    showCopyCurl={typeof onCopyCurl === 'function'}
                    onResponseModeToggle={onResponseModeToggle}
                    onShowThinkingToggle={onShowThinkingToggle}
                    onClearConversation={onClearConversation}
                    onCopyCurl={onCopyCurl}
                    onAttach={onAttach}
                    onVoiceStart={onVoiceStart}
                    onVoiceStop={onVoiceStop}
                    onSend={onSend}
                    canSend={message.trim().length > 0 && !loading}
                    sendLoading={loading}
                  />
                </div>
              </div>
            )}
          </ChatWidgetContainer>
        )}

        {isHistoryOpen && renderHistory?.({ onClose: onHistoryClose })}
    </div>
  );
}
