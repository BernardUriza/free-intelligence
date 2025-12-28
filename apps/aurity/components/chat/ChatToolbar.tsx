'use client';

/**
 * ChatToolbar Component
 *
 * Toolbar with action buttons for chat functionality:
 * - Attach files
 * - Change language
 * - Text formatting
 * - Theme toggle
 * - Voice input
 * - Dynamic persona selector (fetched from backend)
 */

import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Paperclip, Globe, Type, Zap, Trash, Sparkles, BookOpen, Terminal, MoreVertical } from 'lucide-react';
import { confirmDelete, toastSuccess } from '@/lib/swal';
import { VoiceMicButton } from './VoiceMicButton';
import { PersonaSelectorPanel } from './PersonaSelectorPanel';
import { usePersonas } from '@aurity-standalone/hooks/usePersonas';

export type ResponseMode = 'explanatory' | 'concise';
export type PersonaType = string; // Dynamic - fetched from backend

export interface ChatToolbarProps {
  /** Enable/disable attach button */
  showAttach?: boolean;

  /** Enable/disable language button */
  showLanguage?: boolean;

  /** Enable/disable formatting button */
  showFormatting?: boolean;

  /** Enable/disable response mode toggle button */
  showResponseMode?: boolean;

  /** Enable/disable voice button */
  showVoice?: boolean;

  /** Enable/disable persona selector */
  showPersonaSelector?: boolean;

  /** Enable/disable thinking toggle button */
  showThinkingToggle?: boolean;

  /** Current response mode ('explanatory' | 'concise') */
  responseMode?: ResponseMode;

  /** Current selected persona */
  selectedPersona?: PersonaType;

  /** Current thinking visibility state */
  showThinking?: boolean;

  /** Voice recording state (NEW: for VoiceMicButton) */
  voiceRecording?: {
    isRecording: boolean;
    isTranscribing: boolean;
    audioLevel: number;
    isSilent: boolean;
    recordingTime: number;
  };

  /** Callbacks */
  onAttach?: () => void;
  onLanguage?: () => void;
  onFormatting?: () => void;
  onResponseModeToggle?: () => void;
  onPersonaChange?: (persona: PersonaType) => void;
  onVoiceStart?: () => void;
  onVoiceStop?: () => void;
  onShowThinkingToggle?: () => void;
  /** Clear conversation callback */
  onClearConversation?: () => void;
  /** Show copy-curl button (copies a generic TTS curl template) */
  showCopyCurl?: boolean;
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
  selectedPersona = 'general_assistant',
  showThinking = true,
  voiceRecording,
  onAttach,
  onLanguage,
  onFormatting,
  onResponseModeToggle,
  onPersonaChange,
  onVoiceStart,
  onVoiceStop,
  onShowThinkingToggle,
  onClearConversation,
  showCopyCurl = true,
}: ChatToolbarProps) {
  // Fetch personas dynamically from backend (single source of truth)
  const { personas, loading: personasLoading } = usePersonas();

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
        {showPersonaSelector && (
          <PersonaSelectorPanel
            personas={personas}
            selectedPersona={selectedPersona}
            loading={personasLoading}
            onSelect={(personaId) => onPersonaChange?.(personaId)}
          />
        )}

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

                  {/* Curl Template (Developer Tool) */}
                  {showCopyCurl && (
                    <>
                      <div className="chat-dropdown-divider" />
                      <button
                        onClick={async () => {
                          const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';
                          const template = `curl -v -X POST '${BACKEND_URL}/api/tts/synthesize' \\\n  -H 'Content-Type: application/json' \\\n  --data-raw '{"text":"<TU_TEXTO_AQUI>","voice":"nova","provider":"<providerId>","speed":1.0}'`;

                          try {
                            await navigator.clipboard.writeText(template);
                            toastSuccess('Plantilla curl copiada al portapapeles');
                          } catch {
                            // Fallback: do nothing if clipboard unavailable
                          }
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
                      onClick={async () => {
                        const ok = await confirmDelete('conversación');
                        if (ok) {
                          onClearConversation?.();
                          setOverflowOpen(false);
                        }
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
        {/* Clear conversation - destructive action with confirmation modal (hidden when compact) */}
        <button
          onClick={async () => {
            const ok = await confirmDelete('conversación');
            if (ok) onClearConversation?.();
          }}
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
      </div>
    </div>
  );
}
