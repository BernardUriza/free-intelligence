'use client';

/**
 * ChatWidgetHeader Component
 *
 * Header for chat widget with title, subtitle, and control buttons
 * (minimize, maximize/expand, close)
 */

import Link from 'next/link';
import { X, Minimize2, Maximize2, MessageCircle, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { gradients } from '@/lib/styles/gradients';
import type { ChatViewMode } from './ChatWidgetContainer';

export interface ChatWidgetHeaderProps {
  /** Widget title */
  title: string;

  /** Widget subtitle */
  subtitle?: string;

  /** Background gradient classes */
  backgroundClass?: string;

  /** Current view mode */
  mode: ChatViewMode;

  /** Show control buttons (minimize, maximize, close) - defaults to true */
  showControls?: boolean;

  /** Show history search button */
  showHistorySearch?: boolean;

  /** Callbacks - optional when showControls=false */
  onMinimize?: () => void;
  onMaximize?: () => void;
  onToggleDenseMode?: () => void;
  onClose?: () => void;
  onHistorySearch?: () => void;
}

export function ChatWidgetHeader({
  title,
  subtitle,
  backgroundClass = gradients.primaryStrong,
  mode,
  showControls = true,
  showHistorySearch = true,
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
        <Link href="/chat" className="chat-header-icon" title="Abrir chat completo">
          <MessageCircle className="h-5 w-5 text-white" />
        </Link>
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
              <Button onClick={onHistorySearch} className="chat-header-btn" aria-label="Search history" title="Buscar en historial" variant="ghost" size="sm" type="button">
                <Search className="h-4 w-4" />
              </Button>
            )}

            {mode === 'fullscreen' && onToggleDenseMode && (
              <Button onClick={onToggleDenseMode} className="chat-header-btn" aria-label="Cambiar a modo denso" title="Modo denso (sin controles)" variant="ghost" size="sm" type="button">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                  <path d="M0 3.5A1.5 1.5 0 0 1 1.5 2h13A1.5 1.5 0 0 1 16 3.5v9a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 0 12.5v-9zM1.5 3a.5.5 0 0 0-.5.5v9a.5.5 0 0 0 .5.5h13a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-13z"/>
                  <path d="M3 4.5a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5zm0 2a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5zm0 2a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5z"/>
                </svg>
              </Button>
            )}

            {mode === 'dense' && onToggleDenseMode && (
              <Button onClick={onToggleDenseMode} className="chat-header-btn" aria-label="Cambiar a modo expandido" title="Modo expandido (con controles)" variant="ghost" size="sm" type="button">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                  <path d="M14 1a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h12zM2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2z"/>
                  <path d="M6.5 4.5a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1 0-1h2V5a.5.5 0 0 1 .5-.5zM8 8.5a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1 0-1h2v-2a.5.5 0 0 1 .5-.5zm3-4a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1 0-1h2V5a.5.5 0 0 1 .5-.5zm0 6a.5.5 0 0 1 .5.5v3a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1 0-1h2v-2a.5.5 0 0 1 .5-.5z"/>
                </svg>
              </Button>
            )}

            {mode === 'expanded' && (
              <Button onClick={onMinimize} className="chat-header-btn" aria-label="Restaurar tamaño" title="Restaurar a tamaño normal" variant="ghost" size="sm" type="button">
                <Minimize2 className="h-4 w-4" />
              </Button>
            )}

            {mode === 'normal' && (
              <Button onClick={onMaximize} className="chat-header-btn" aria-label="Expandir" title="Expandir (60% más grande)" variant="ghost" size="sm" type="button">
                <Maximize2 className="h-4 w-4" />
              </Button>
            )}

            <Button onClick={onClose} className="chat-header-btn" aria-label="Close" title="Cerrar" variant="ghost" size="sm" type="button">
              <X className="h-5 w-5" />
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
