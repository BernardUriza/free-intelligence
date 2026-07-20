'use client';

/**
 * fi-glass · ChatWidgetHeader — title + control buttons (minimize / maximize /
 * dense / close / history).
 *
 * Two app couplings inverted for the shell:
 * - `@/components/ui/button` → inline `<button class="fi-btn-ghost fi-btn-sm …">`
 *   (the exact class output of `<Button variant="ghost" size="sm">`, so the
 *   rendered markup is identical — render-diff safe).
 * - `<Link href="/chat">` → `onNavigate('chat')` (typed callback, no next/link).
 */

import { X, Minimize2, Maximize2, MessageCircle, Search } from 'lucide-react';
import type { ChatViewMode, ChatNavDest } from 'fi-glass/shell';

/** Mirrors `<Button variant="ghost" size="sm" className="chat-header-btn">`. */
const HEADER_BTN_CLASS = 'fi-btn-ghost fi-btn-sm chat-header-btn';

/** Fallback header gradient (apps pass config.theme.background.header). */
const DEFAULT_HEADER_GRADIENT = 'bg-gradient-to-r from-emerald-600 to-cyan-600';

export interface ChatWidgetHeaderProps {
  title: string;
  subtitle?: string;
  backgroundClass?: string;
  mode: ChatViewMode;
  showControls?: boolean;
  showHistorySearch?: boolean;
  onNavigate?: (dest: ChatNavDest) => void;
  onMinimize?: () => void;
  onMaximize?: () => void;
  onToggleDenseMode?: () => void;
  onClose?: () => void;
  onHistorySearch?: () => void;
}

export function ChatWidgetHeader({
  title,
  subtitle,
  backgroundClass = DEFAULT_HEADER_GRADIENT,
  mode,
  showControls = true,
  showHistorySearch = true,
  onNavigate,
  onMinimize,
  onMaximize,
  onToggleDenseMode,
  onClose,
  onHistorySearch,
}: ChatWidgetHeaderProps) {
  return (
    <div className={`${backgroundClass} chat-header`}>
      {/* Left: Icon + Title */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          onClick={() => onNavigate?.('chat')}
          className="chat-header-icon"
          title="Abrir chat completo"
          aria-label="Abrir chat completo"
        >
          <MessageCircle className="h-5 w-5 text-white" />
        </button>
        <div className="min-w-0">
          <h3 className="chat-header-title">{title}</h3>
          {subtitle && <p className="chat-header-subtitle">{subtitle}</p>}
        </div>
      </div>

      {/* Right: Control Buttons */}
      <div className="chat-header-controls">
        {showControls && (
          <>
            {showHistorySearch && onHistorySearch && mode !== 'minimized' && (
              <button onClick={onHistorySearch} className={HEADER_BTN_CLASS} aria-label="Search history" title="Buscar en historial" type="button">
                <Search className="h-4 w-4" />
              </button>
            )}

            {mode === 'fullscreen' && onToggleDenseMode && (
              <button onClick={onToggleDenseMode} className={HEADER_BTN_CLASS} aria-label="Cambiar a modo denso" title="Modo denso (sin controles)" type="button">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                  <path d="M0 3.5A1.5 1.5 0 0 1 1.5 2h13A1.5 1.5 0 0 1 16 3.5v9a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 0 12.5v-9zM1.5 3a.5.5 0 0 0-.5.5v9a.5.5 0 0 0 .5.5h13a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-13z"/>
                  <path d="M3 4.5a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5zm0 2a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5zm0 2a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5z"/>
                </svg>
              </button>
            )}

            {mode === 'dense' && onToggleDenseMode && (
              <button onClick={onToggleDenseMode} className={HEADER_BTN_CLASS} aria-label="Cambiar a modo expandido" title="Modo expandido (con controles)" type="button">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                  <path d="M14 1a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h12zM2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2z"/>
                  <path d="M6.5 4.5a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1 0-1h2V5a.5.5 0 0 1 .5-.5zM8 8.5a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1 0-1h2v-2a.5.5 0 0 1 .5-.5zm3-4a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1 0-1h2V5a.5.5 0 0 1 .5-.5zm0 6a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1 0-1h2v-2a.5.5 0 0 1 .5-.5z"/>
                </svg>
              </button>
            )}

            {mode === 'expanded' && (
              <button onClick={onMinimize} className={HEADER_BTN_CLASS} aria-label="Restaurar tamaño" title="Restaurar a tamaño normal" type="button">
                <Minimize2 className="h-4 w-4" />
              </button>
            )}

            {mode === 'normal' && (
              <button onClick={onMaximize} className={HEADER_BTN_CLASS} aria-label="Expandir" title="Expandir (60% más grande)" type="button">
                <Maximize2 className="h-4 w-4" />
              </button>
            )}

            <button onClick={onClose} className={HEADER_BTN_CLASS} aria-label="Close" title="Cerrar" type="button">
              <X className="h-5 w-5" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}
