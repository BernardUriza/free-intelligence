'use client';

/**
 * fi-glass · ChatToolbar — the toolbar SHELL (layout + generic controls).
 *
 * Slot-injection per the Curio scope: the persona selector (aurity's
 * PersonaSelectorPanel, bound to `@/components/ui/select`) is NOT here — it is
 * passed in as the `personaSelector` slot. The other app couplings are inverted
 * to callbacks so fi-glass imports no app modules:
 * - swal confirm on "clear conversation" → app wraps `onClearConversation`.
 * - curl dev-tool (app routes/env + toast) → `onCopyCurl` callback.
 * - voice mic → fi-glass/voice `VoiceMicButton`.
 */

import { Paperclip, Globe, Type, Zap, Trash, Sparkles, BookOpen, Terminal, MoreVertical, Send, Loader2 } from 'lucide-react';
import type { ReactNode } from 'react';
import { ActionMenu } from '../menu/ActionMenu';
import { VoiceMicButton } from '../voice';
import type { ResponseMode, PersonaType, VoiceRecordingState } from './types';

export interface ChatToolbarProps {
  showAttach?: boolean;
  showLanguage?: boolean;
  showFormatting?: boolean;
  showResponseMode?: boolean;
  showVoice?: boolean;
  showPersonaSelector?: boolean;
  showThinkingToggle?: boolean;
  responseMode?: ResponseMode;
  selectedPersona?: PersonaType;
  showThinking?: boolean;
  voiceRecording?: VoiceRecordingState;
  /** Persona selector SLOT (app's PersonaSelectorPanel). */
  personaSelector?: ReactNode;
  onAttach?: () => void;
  onLanguage?: () => void;
  onFormatting?: () => void;
  onResponseModeToggle?: () => void;
  onVoiceStart?: () => void;
  onVoiceStop?: () => void;
  onShowThinkingToggle?: () => void;
  /** Show the clear-conversation control (off when no handler is wired). */
  showClear?: boolean;
  /** Clear conversation — the app wraps this with its confirm dialog. */
  onClearConversation?: () => void;
  /** Show copy-curl dev tool button. */
  showCopyCurl?: boolean;
  /** Copy-curl handler — the app builds the template + toasts. */
  onCopyCurl?: () => void;
  onSend?: () => void;
  canSend?: boolean;
  sendLoading?: boolean;
}

export function ChatToolbar({
  showAttach = true,
  showLanguage = true,
  showFormatting = true,
  showResponseMode = true,
  showVoice = true,
  showPersonaSelector = true,
  showThinkingToggle = true,
  responseMode = 'explanatory',
  selectedPersona: _selectedPersona = 'general_assistant',
  showThinking = true,
  voiceRecording,
  personaSelector,
  onAttach,
  onLanguage,
  onFormatting,
  onResponseModeToggle,
  onVoiceStart,
  onVoiceStop,
  onShowThinkingToggle,
  showClear = true,
  onClearConversation,
  showCopyCurl = true,
  onCopyCurl,
  onSend,
  canSend = false,
  sendLoading = false,
}: ChatToolbarProps) {
  // Semantic classes from chat.css (Tailwind v4 migration)
  const buttonBaseClass = "chat-toolbar-btn";
  const iconClass = "chat-toolbar-icon";

  return (
    <div className="chat-toolbar">
      {/* Left side: Persona selector + Overflow menu */}
      <div className="fi-flex-gap-sm">
        {showPersonaSelector && personaSelector}

        {/* Overflow menu for secondary actions — the framework's ActionMenu now,
            not a second hand-written dropdown. Same trigger, same items, same
            classes, same order: this toolbar IS the SSOT of that anatomy, so the
            extraction had to preserve it exactly (dividers, per-item dress and
            the compact-only gates included). */}
        <ActionMenu
          trigger={<MoreVertical className={iconClass} />}
          triggerLabel="Más opciones"
          triggerClassName={buttonBaseClass}
          menuClassName="chat-dropdown"
          itemClassName="chat-dropdown-item"
          dividerClassName="chat-dropdown-divider"
          actions={[
            ...(showAttach
              ? [
                  {
                    id: 'attach',
                    label: 'Adjuntar archivo',
                    icon: <Paperclip className="fi-icon-sm" />,
                    onSelect: () => onAttach?.(),
                  },
                ]
              : []),
            ...(showLanguage
              ? [
                  {
                    id: 'language',
                    label: 'Cambiar idioma',
                    icon: <Globe className="fi-icon-sm" />,
                    onSelect: () => onLanguage?.(),
                  },
                ]
              : []),
            ...(showFormatting
              ? [
                  {
                    id: 'formatting',
                    label: 'Formato de texto',
                    icon: <Type className="fi-icon-sm" />,
                    onSelect: () => onFormatting?.(),
                  },
                ]
              : []),
            ...(showCopyCurl
              ? [
                  {
                    id: 'curl',
                    label: 'Copiar plantilla curl',
                    icon: <Terminal className="fi-icon-sm" />,
                    onSelect: () => onCopyCurl?.(),
                    dividerBefore: true,
                    className:
                      'chat-dropdown-item fi-text-warning hover:bg-amber-900/20 hover:text-amber-300',
                  },
                ]
              : []),
            ...(showThinkingToggle
              ? [
                  {
                    id: 'thinking',
                    label: showThinking ? 'Ocultar razonamiento' : 'Mostrar razonamiento',
                    icon: <Sparkles className="fi-icon-sm" />,
                    onSelect: () => onShowThinkingToggle?.(),
                    dividerBefore: true,
                    wrapperClassName: '@md:hidden',
                    className: `chat-dropdown-item ${showThinking ? 'fi-text-purple hover:bg-purple-900/20' : ''}`,
                  },
                ]
              : []),
            ...(showClear
              ? [
                  {
                    id: 'clear',
                    label: 'Limpiar conversación',
                    icon: <Trash className="fi-icon-sm" />,
                    onSelect: () => onClearConversation?.(),
                    dividerBefore: true,
                    wrapperClassName: '@md:hidden',
                    className: 'chat-dropdown-item-danger',
                  },
                ]
              : []),
          ]}
        />
      </div>

      {/* Right side: Response Mode, Thinking Toggle & Voice */}
      <div className="fi-flex-gap-sm">
        {/* Clear conversation - destructive action (app confirms; hidden when compact) */}
        {showClear && (
          <button
            onClick={() => onClearConversation?.()}
            className={`${buttonBaseClass} chat-toolbar-btn-danger hidden @md:flex`}
            title="Limpiar conversación"
            aria-label="Limpiar conversación"
          >
            <Trash className={iconClass} />
          </button>
        )}

        {/* ThinkingToggle - hidden when compact, shown in overflow menu instead */}
        {showThinkingToggle && (
          <button
            onClick={onShowThinkingToggle}
            className={`${buttonBaseClass} hidden @md:flex ${showThinking ? 'chat-toolbar-btn-active' : ''}`}
            title={showThinking ? 'Razonamiento visible (click para ocultar)' : 'Razonamiento oculto (click para mostrar)'}
            aria-label={showThinking ? 'Ocultar razonamiento del modelo' : 'Mostrar razonamiento del modelo'}
          >
            <Sparkles className={iconClass} />
          </button>
        )}

        {showResponseMode && (
          <button
            onClick={onResponseModeToggle}
            className={`${buttonBaseClass} ${responseMode === 'concise' ? 'fi-text-info hover:text-cyan-300' : 'chat-toolbar-btn-success'}`}
            title={responseMode === 'explanatory' ? 'Modo: Explicativo (detallado)' : 'Modo: Conciso (breve)'}
            aria-label={responseMode === 'explanatory' ? 'Cambiar a modo conciso' : 'Cambiar a modo explicativo'}
          >
            {responseMode === 'explanatory' ? (
              <BookOpen className={iconClass} />
            ) : (
              <Zap className={iconClass} />
            )}
          </button>
        )}

        {showVoice && (
          <VoiceMicButton
            isRecording={voiceRecording?.isRecording || false}
            isTranscribing={voiceRecording?.isTranscribing || false}
            audioLevel={voiceRecording?.audioLevel || 0}
            isSilent={voiceRecording?.isSilent ?? true}
            recordingTime={voiceRecording?.recordingTime || 0}
            onStart={onVoiceStart || (() => {})}
            onStop={onVoiceStop || (() => {})}
          />
        )}

        {/* Send Button (ChatGPT style - in toolbar) */}
        <button
          onClick={onSend}
          disabled={!canSend}
          className={`p-2.5 rounded-xl flex items-center justify-center flex-shrink-0 transition-all duration-200 ${
            canSend
              ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-slate-900 shadow-lg shadow-amber-500/25 hover:shadow-amber-500/40'
              : 'bg-slate-800 text-slate-500 cursor-not-allowed'
          }`}
          aria-label="Enviar mensaje"
        >
          {sendLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}
