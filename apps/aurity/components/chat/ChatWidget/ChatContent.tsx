/**
 * ChatContent Component
 *
 * The main chat UI content when widget is open.
 * SOLID: Single Responsibility - only chat UI rendering.
 */

import { useMemo } from 'react';
import { Loader2 } from 'lucide-react';
import { ChatWidgetContainer } from '../ChatWidgetContainer';
import { ChatWidgetHeader } from '../ChatWidgetHeader';
import { ChatWidgetMessages } from '../ChatWidgetMessages';
import { ChatWidgetInput } from '../ChatWidgetInput';
import { ChatToolbar } from '../ChatToolbar';
import { ChatFilePreview, type UploadStatus } from '../ChatFilePreview';
import { ChatStartScreen } from '../ChatStartScreen';
import { HistorySearch, type InteractionResult } from '../HistorySearch';
import { usePersonas } from '@aurity-standalone/hooks/usePersonas';
import type { ChatConfig } from '@/config/chat.config';
import type { FIMessage } from '@aurity-standalone/types/assistant';
import type { ChatViewMode, VoiceRecordingState } from './types';
import type { ResponseMode, PersonaType } from '../ChatToolbar';

export interface ChatContentProps {
  // Config
  config: ChatConfig;
  embedded: boolean;
  isAuthenticated: boolean;
  userName?: string;

  // Widget state
  viewMode: ChatViewMode;
  isHistoryOpen: boolean;
  conversationStarted: boolean;
  isStartingConversation: boolean;

  // Chat state
  messages: FIMessage[];
  loading: boolean;
  isTyping: boolean;
  loadingInitial: boolean;
  hasMoreMessages: boolean;
  loadingOlder: boolean;
  customEmptyState?: React.ReactNode;
  customQuickReplies?: React.ReactNode;

  // Input state
  message: string;

  // Preferences
  responseMode: ResponseMode;
  selectedPersona: PersonaType;
  showThinking?: boolean;

  // Voice state
  voiceState: VoiceRecordingState;

  // File upload state
  uploadFile: File | null;
  uploadStatus: UploadStatus;
  isUploadActive: boolean;

  // Streaming state
  streaming?: {
    status: 'idle' | 'streaming' | 'complete' | 'error';
    content: string;
    thinking: string;
    isStreaming: boolean;
  };

  // Actions
  onModeChange: (mode: ChatViewMode) => void;
  onMinimize: () => void;
  onMaximize: () => void;
  onToggleDenseMode: () => void;
  onClose: () => void;
  onHistoryOpen: () => void;
  onHistoryClose: () => void;
  onStartConversation: () => void;
  onLogin: () => void;
  onLoadOlder: () => Promise<void>;
  onMessageChange: (message: string) => void;
  onSend: () => void;
  onResponseModeToggle: () => void;
  onShowThinkingToggle?: () => void;
  onPersonaChange: (persona: PersonaType) => void;
  onClearConversation?: () => void;
  onVoiceStart: () => void;
  onVoiceStop: () => void;
  onAttach: () => void;
  onCancelUpload: () => void;
}

export function ChatContent({
  config,
  embedded,
  isAuthenticated,
  userName,
  viewMode,
  isHistoryOpen,
  conversationStarted: _conversationStarted,
  isStartingConversation,
  messages,
  loading,
  isTyping,
  loadingInitial,
  hasMoreMessages,
  loadingOlder,
  customEmptyState,
  customQuickReplies,
  message,
  responseMode,
  selectedPersona,
  showThinking = true,
  voiceState,
  uploadFile,
  uploadStatus,
  isUploadActive,
  streaming,
  onModeChange,
  onMinimize,
  onMaximize,
  onToggleDenseMode,
  onClose,
  onHistoryOpen,
  onHistoryClose,
  onStartConversation,
  onLogin,
  onLoadOlder,
  onMessageChange,
  onSend,
  onResponseModeToggle,
  onShowThinkingToggle,
  onPersonaChange,
  onClearConversation,
  onVoiceStart,
  onVoiceStop,
  onAttach,
  onCancelUpload,
}: ChatContentProps) {
  // Get personas to find the selected persona's name
  const { personas } = usePersonas();

  // Find the selected persona's display name
  const personaName = useMemo(() => {
    const persona = personas.find(p => p.id === selectedPersona);
    return persona?.name || 'Asistente';
  }, [personas, selectedPersona]);

  // Dynamic placeholder like ChatGPT: "Escribe a [Persona Name]"
  const dynamicPlaceholder = `Escribe a ${personaName}...`;

  // Override config.behavior.showThinking with preference
  // MEMOIZED to prevent re-renders of ChatMessageList on every keystroke
  const configWithPrefs = useMemo<ChatConfig>(() => ({
    ...config,
    behavior: {
      ...config.behavior,
      showThinking,
    },
  }), [config, showThinking]);

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
                onMinimize={onMinimize}
                onMaximize={onMaximize}
                onToggleDenseMode={onToggleDenseMode}
                onClose={onClose}
                onHistorySearch={onHistoryOpen}
              />
            )}

            {messages.length === 0 && loadingInitial ? (
              <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
              </div>
            ) : messages.length === 0 && !isTyping && customEmptyState ? (
              customEmptyState
            ) : messages.length === 0 && !isTyping ? (
              <ChatStartScreen
                isAuthenticated={isAuthenticated}
                userName={userName}
                onStart={onStartConversation}
                onLogin={onLogin}
                isLoading={isStartingConversation}
              />
            ) : (
              <ChatWidgetMessages
                messages={messages}
                loadingInitial={loadingInitial}
                isTyping={isTyping}
                config={configWithPrefs}
                mode={viewMode}
                selectedPersona={selectedPersona}
                onLoadOlder={onLoadOlder}
                hasMoreMessages={hasMoreMessages}
                loadingOlder={loadingOlder}
                streaming={streaming}
              />
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
                      status={uploadStatus}
                      onCancel={onCancelUpload}
                    />
                  )}

                  {/* Input ARRIBA - solo textarea */}
                  <ChatWidgetInput
                    message={message}
                    loading={loading}
                    placeholder={dynamicPlaceholder}
                    onMessageChange={onMessageChange}
                    onSend={onSend}
                  />

                  {/* Toolbar ABAJO - con botones + mic + send */}
                  <ChatToolbar
                    responseMode={responseMode}
                    selectedPersona={selectedPersona}
                    showThinking={showThinking}
                    voiceRecording={voiceState}
                    showAttach={true}
                    showLanguage={false}
                    showFormatting={false}
                    showResponseMode={true}
                    showVoice={true}
                    showPersonaSelector={true}
                    showThinkingToggle={true}
                    onResponseModeToggle={onResponseModeToggle}
                    onShowThinkingToggle={onShowThinkingToggle}
                    onClearConversation={onClearConversation}
                    onPersonaChange={onPersonaChange}
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

        {isHistoryOpen && (
          <HistorySearch
            onClose={onHistoryClose}
            onSelectResult={(_result: InteractionResult) => {
              onHistoryClose();
            }}
          />
        )}
    </div>
  );
}
