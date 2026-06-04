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

import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Paperclip, Globe, Type, Zap, Trash, Sparkles, BookOpen, Terminal, MoreVertical, Send, Loader2 } from 'lucide-react';
import type { ReactNode } from 'react';
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
  onClearConversation,
  showCopyCurl = true,
  onCopyCurl,
  onSend,
  canSend = false,
  sendLoading = false,
}: ChatToolbarProps) {
  // Overflow menu state
  const [overflowOpen, setOverflowOpen] = useState(false);
  const overflowButtonRef = useRef<HTMLButtonElement>(null);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });

  // Calculate dropdown position when opening
  useEffect(() => {
    if (overflowOpen && overflowButtonRef.current) {
      const rect = overflowButtonRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.top - 8, // 8px margin above button
        left: rect.left,
      });
    }
  }, [overflowOpen]);

  // Semantic classes from chat.css (Tailwind v4 migration)
  const buttonBaseClass = "chat-toolbar-btn";
  const iconClass = "chat-toolbar-icon";

  return (
    <div className="chat-toolbar">
      {/* Left side: Persona selector + Overflow menu */}
      <div className="fi-flex-gap-sm">
        {showPersonaSelector && personaSelector}

        {/* Overflow menu for secondary actions */}
        {(showAttach || showLanguage || showFormatting) && (
          <div className="relative">
            <button
              ref={overflowButtonRef}
              onClick={() => setOverflowOpen(!overflowOpen)}
              className={buttonBaseClass}
              title="Más opciones"
              aria-label="Más opciones"
            >
              <MoreVertical className={iconClass} />
            </button>

            {overflowOpen && createPortal(
              <>
                {/* Backdrop */}
                <div
                  className="fixed inset-0 z-[9998]"
                  onClick={() => setOverflowOpen(false)}
                  aria-hidden="true"
                />

                {/* Dropdown Menu - Portal renders outside overflow:hidden container */}
                <div
                  className="chat-dropdown"
                  style={{
                    top: dropdownPosition.top,
                    left: dropdownPosition.left,
                    transform: 'translateY(-100%)',
                  }}
                >
                  {/* Attach */}
                  {showAttach && (
                    <button
                      onClick={() => {
                        onAttach?.();
                        setOverflowOpen(false);
                      }}
                      className="chat-dropdown-item"
                    >
                      <Paperclip className="fi-icon-sm" />
                      <span>Adjuntar archivo</span>
                    </button>
                  )}

                  {/* Language */}
                  {showLanguage && (
                    <button
                      onClick={() => {
                        onLanguage?.();
                        setOverflowOpen(false);
                      }}
                      className="chat-dropdown-item"
                    >
                      <Globe className="fi-icon-sm" />
                      <span>Cambiar idioma</span>
                    </button>
                  )}

                  {/* Formatting */}
                  {showFormatting && (
                    <button
                      onClick={() => {
                        onFormatting?.();
                        setOverflowOpen(false);
                      }}
                      className="chat-dropdown-item"
                    >
                      <Type className="fi-icon-sm" />
                      <span>Formato de texto</span>
                    </button>
                  )}

                  {/* Curl Template (Developer Tool) — app builds + copies + toasts */}
                  {showCopyCurl && (
                    <>
                      <div className="chat-dropdown-divider" />
                      <button
                        onClick={() => {
                          onCopyCurl?.();
                          setOverflowOpen(false);
                        }}
                        className="chat-dropdown-item fi-text-warning hover:bg-amber-900/20 hover:text-amber-300"
                      >
                        <Terminal className="fi-icon-sm" />
                        <span>Copiar plantilla curl</span>
                      </button>
                    </>
                  )}

                  {/* Compact-only: ThinkingToggle (hidden when container is wider) */}
                  {showThinkingToggle && (
                    <div className="@md:hidden">
                      <div className="chat-dropdown-divider" />
                      <button
                        onClick={() => {
                          onShowThinkingToggle?.();
                          setOverflowOpen(false);
                        }}
                        className={`chat-dropdown-item ${showThinking ? 'fi-text-purple hover:bg-purple-900/20' : ''}`}
                      >
                        <Sparkles className="fi-icon-sm" />
                        <span>{showThinking ? 'Ocultar razonamiento' : 'Mostrar razonamiento'}</span>
                      </button>
                    </div>
                  )}

                  {/* Compact-only: Clear conversation (hidden when container is wider) */}
                  <div className="@md:hidden">
                    <div className="chat-dropdown-divider" />
                    <button
                      onClick={() => {
                        onClearConversation?.();
                        setOverflowOpen(false);
                      }}
                      className="chat-dropdown-item-danger"
                    >
                      <Trash className="fi-icon-sm" />
                      <span>Limpiar conversación</span>
                    </button>
                  </div>
                </div>
              </>,
              document.body
            )}
          </div>
        )}
      </div>

      {/* Right side: Response Mode, Thinking Toggle & Voice */}
      <div className="fi-flex-gap-sm">
        {/* Clear conversation - destructive action (app confirms; hidden when compact) */}
        <button
          onClick={() => onClearConversation?.()}
          className={`${buttonBaseClass} chat-toolbar-btn-danger hidden @md:flex`}
          title="Limpiar conversación"
          aria-label="Limpiar conversación"
        >
          <Trash className={iconClass} />
        </button>

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
