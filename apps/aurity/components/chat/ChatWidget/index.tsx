'use client';

/**
 * AurityChatWidget — the aurity composition root for the fi-glass chat shell.
 *
 * This is the thin wrapper (Curio, element 96): it owns all DOMAIN concerns —
 * useAuth, useFIConversation, useChatPreferences/usePersonas, useVoiceInput,
 * useFileUploadState, useBreakpoints, the `message` text state (voice mutates
 * it), next-router navigation, the swal-confirmed clear + curl dev-tool — and
 * passes them into fi-glass's presentational <ChatWidget> along with the three
 * domain SLOTS (persona selector / history / messages) that stay in aurity.
 *
 * Exported as `ChatWidget` so existing consumers (ConditionalChatWidget,
 * app/chat/page, ReceptionistChatWidget, ProtectedChatWidget) keep importing
 * `@/components/chat/ChatWidget` unchanged. Same as Americio's ChatWidgetInput
 * wrapping fi-glass's Composer.
 *
 * Architecture:
 *   AurityChatWidget → fi-glass <ChatWidget> → ChatContent → useChat → /assistant/chat
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { useFIConversation } from '@aurity-standalone/hooks/useFIConversation';
import { usePersonas } from '@aurity-standalone/hooks/usePersonas';
import { useBreakpoints } from '@/hooks/useMediaQuery';
import { defaultChatConfig, type ChatConfig, CHAT_BREAKPOINTS } from '@/config/chat.config';
import { confirmDelete, toastSuccess } from '@/lib/swal';
import { ROUTES } from '@/lib/api/routes';
import {
  ChatWidget as GlassChatWidget,
  type ChatViewMode,
  type ChatNavDest,
} from 'fi-glass/shell';
import type { ChatHook } from '@aurity-standalone/types/chat';

import { useChatPreferences } from './useChatPreferences';
import { useVoiceInput } from './useVoiceInput';
import { useFileUploadState } from './useFileUploadState';
import { ChatInstructionsPrompt } from '../ChatInstructionsPrompt';
import { PersonaSelectorPanel } from '../PersonaSelectorPanel';
import { HistorySearch, type InteractionResult } from '../HistorySearch';
import { ChatWidgetMessages } from '../ChatWidgetMessages';

export interface ChatWidgetProps {
  /** Custom configuration (optional) */
  config?: Partial<ChatConfig>;
  /** Start with chat open (default: false) */
  initialOpen?: boolean;
  /** Initial view mode (default: 'normal') */
  initialMode?: ChatViewMode;
  /** Hide the floating button when closed - for embedded/page usage */
  embedded?: boolean;
  /** Dependency-injected chat hook (defaults to useFIConversation) */
  chatHook?: ChatHook;
}

export function ChatWidget({
  config: customConfig,
  initialOpen = false,
  initialMode = 'normal',
  embedded = false,
  chatHook,
}: ChatWidgetProps = {}) {
  const router = useRouter();
  const { user, isAuthenticated, loginWithRedirect } = useAuth();
  const { isMobile } = useBreakpoints(CHAT_BREAKPOINTS);
  const { personas } = usePersonas();
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

  const preferences = useChatPreferences();
  const storageKey = user?.sub ? `fi_chat_widget_${user.sub}` : undefined;

  // Context updates when persona/responseMode change
  const chatContext = useMemo(() => {
    const personaId = typeof preferences.selectedPersona === 'string' && preferences.selectedPersona
      ? preferences.selectedPersona
      : 'general_assistant';
    return {
      doctor_id: user?.sub,
      doctor_name: user?.name,
      persona: personaId,
      response_mode: preferences.responseMode,
    };
  }, [user?.sub, user?.name, preferences.selectedPersona, preferences.responseMode]);

  // Default chat hook (injectable for non-default consumers)
  const defaultChatHook = useFIConversation({
    phase: undefined,
    context: chatContext,
    storageKey,
    autoIntroduction: false,
    responseMode: preferences.responseMode,
  });

  const hook: ChatHook = (chatHook ?? defaultChatHook) as ChatHook;
  const {
    messages,
    loading,
    isTyping,
    loadingInitial = false,
    sendMessageStream,
    streaming,
    loadOlderMessages = async () => {},
    hasMoreMessages = false,
    loadingOlder = false,
    clearConversation,
  } = hook;

  // Voice input (domain: useChatVoiceRecorder STT) — mutates `message`
  const voiceInput = useVoiceInput({
    userId: user?.sub || 'anonymous',
    message,
    setMessage,
  });

  // File upload (domain: useChatUpload)
  const fileUpload = useFileUploadState({
    persona: preferences.selectedPersona || 'assistant',
    userId: user?.sub || undefined,
  });

  const selectedPersona = preferences.selectedPersona || 'assistant';
  const personaName = useMemo(
    () => personas.find((p) => p.id === selectedPersona)?.name || 'Asistente',
    [personas, selectedPersona]
  );

  // Send via streaming
  const handleSend = useCallback(async () => {
    if (!message.trim() || loading) return;
    const userMessage = message.trim();
    setMessage('');
    if (sendMessageStream) {
      await sendMessageStream(userMessage);
    }
  }, [message, loading, sendMessageStream]);

  // Auth0 login
  const handleLogin = useCallback(() => {
    loginWithRedirect({ appState: { returnTo: window.location.pathname } });
  }, [loginWithRedirect]);

  // Typed navigation (was 3 hardcoded next/link hrefs)
  const handleNavigate = useCallback(
    (dest: ChatNavDest) => {
      const map: Record<ChatNavDest, string> = {
        chat: '/chat',
        downloads: '/downloads',
        personas: '/admin/personas/',
      };
      router.push(map[dest]);
    },
    [router]
  );

  // Clear conversation with confirm (swal stays in aurity)
  const handleClearConversation = useCallback(async () => {
    const ok = await confirmDelete('conversación');
    if (ok) clearConversation?.();
  }, [clearConversation]);

  // Copy-curl dev tool (routes/env/toast stay in aurity)
  const handleCopyCurl = useCallback(async () => {
    const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';
    const template = `curl -v -X POST '${BACKEND_URL}${ROUTES.tts}/synthesize' \\\n  -H 'Content-Type: application/json' \\\n  --data-raw '{"text":"<TU_TEXTO_AQUI>","voice":"nova","provider":"<providerId>","speed":1.0}'`;
    try {
      await navigator.clipboard.writeText(template);
      toastSuccess('Plantilla curl copiada al portapapeles');
    } catch {
      // Fallback: do nothing if clipboard unavailable
    }
  }, []);

  // Cross-tab memory clear (moved from the old orchestrator — needs setMessage)
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

  // Streaming map (thinking → streaming) for the messages slot
  const streamingForMessages = streaming && {
    status: streaming.status === 'thinking' ? 'streaming' : (streaming.status as 'idle' | 'streaming' | 'complete' | 'error'),
    content: streaming.content,
    thinking: streaming.thinking,
    isStreaming: streaming.isStreaming,
  };

  // Config with the showThinking preference applied (for the messages slot)
  const configWithPrefs: ChatConfig = useMemo(
    () => ({ ...config, behavior: { ...config.behavior, showThinking: preferences.showThinking } }),
    [config, preferences.showThinking]
  );

  return (
    <GlassChatWidget
      chatHook={hook}
      config={config}
      user={user}
      isAuthenticated={isAuthenticated}
      onLogin={handleLogin}
      onNavigate={handleNavigate}
      isMobile={isMobile}
      initialOpen={initialOpen}
      initialMode={initialMode}
      embedded={embedded}
      message={message}
      onMessageChange={setMessage}
      onSend={handleSend}
      responseMode={preferences.responseMode}
      selectedPersona={selectedPersona}
      personaName={personaName}
      showThinking={preferences.showThinking}
      onResponseModeToggle={preferences.toggleResponseMode}
      onShowThinkingToggle={preferences.toggleShowThinking}
      onPersonaChange={preferences.setPersona}
      onClearConversation={handleClearConversation}
      voiceState={voiceInput.voiceState}
      onVoiceStart={voiceInput.startVoice}
      onVoiceStop={voiceInput.stopVoice}
      uploadFile={fileUpload.file}
      uploadStatus={fileUpload.status}
      isUploadActive={fileUpload.isActive}
      onAttach={fileUpload.openPicker}
      // The staged step the migration to the monorepo left unwired:
      // ChatInstructionsPrompt existed, nothing mounted it, so setInstructions was
      // never called and every upload parked in `pending_instructions` — indexing
      // never started and the chip span "Procesando…" with no way out.
      uploadPrompt={
        fileUpload.isPending && fileUpload.file ? (
          <ChatInstructionsPrompt
            filename={fileUpload.file.name}
            onSelect={(instruction) => void fileUpload.setInstructions(instruction)}
            onCancel={fileUpload.cancel}
          />
        ) : undefined
      }
      onCancelUpload={fileUpload.cancel}
      onCopyCurl={handleCopyCurl}
      personaSelector={
        <PersonaSelectorPanel
          personas={personas}
          selectedPersona={selectedPersona}
          loading={preferences.personasLoading}
          onSelect={(personaId) => preferences.setPersona(personaId)}
        />
      }
      renderHistory={({ onClose }) => (
        <HistorySearch
          onClose={onClose}
          onSelectResult={(_result: InteractionResult) => onClose()}
        />
      )}
      renderMessages={({ viewMode }) => (
        <ChatWidgetMessages
          messages={messages}
          loadingInitial={loadingInitial}
          isTyping={isTyping}
          config={configWithPrefs}
          mode={viewMode}
          selectedPersona={selectedPersona}
          onLoadOlder={loadOlderMessages}
          hasMoreMessages={hasMoreMessages}
          loadingOlder={loadingOlder}
          streaming={streamingForMessages}
        />
      )}
    />
  );
}

export { ChatWidget as AurityChatWidget };
