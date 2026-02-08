/**
 * ReasoningBlock - AI Thinking/Reasoning Display Component
 *
 * Best Practices 2025-2026:
 * - Visible "thought log" for transparency & trust
 * - Collapsible with smooth animations
 * - Streaming support with live updates
 * - Accessible ARIA labels
 *
 * @see https://fuselabcreative.com/ui-design-for-ai-agents/
 * Updated: 2025-12-12
 */

import React, { useState, useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';
import { getPersonaIcon } from '@/components/ui/message/styles/persona-styles';
import { Button } from '@/components/ui/button';
import { Copy, Check } from 'lucide-react';

/**
 * Persona display names mapping
 */
const PERSONA_DISPLAY_NAMES: Record<string, string> = {
  general_assistant: 'Asistente General',
  soap_editor: 'Editor SOAP',
  clinical_advisor: 'Asesor Clínico',
  onboarding_guide: 'Guía de Onboarding',
  pattern_weaver: 'Tejedor de Patrones',
  sovereignty_guide: 'Guía de Soberanía',
  growth_mirror: 'Espejo de Crecimiento',
  honest_limiter: 'Limitador Honesto',
};

/**
 * Get persona display name
 */
function getPersonaDisplayName(persona?: string): string {
  if (!persona) return 'AURITY';
  return PERSONA_DISPLAY_NAMES[persona] || 'AURITY';
}

interface ReasoningBlockProps {
  /** Block title */
  title?: string;
  /** Thinking/reasoning content */
  thinking: string;
  /** Message ID for persistence */
  messageId?: string;
  /** Whether content is still streaming */
  isStreaming?: boolean;
  /** Compact mode for inline display */
  compact?: boolean;
  /** Custom className */
  className?: string;
  /** Persona ID for icon and name */
  persona?: string;
}

// Animated brain icon for thinking state
function ThinkingIcon({ isAnimating = false }: { isAnimating?: boolean }) {
  return (
    <svg
      className={cn(
        'w-4 h-4 transition-all duration-300',
        isAnimating && 'animate-pulse text-violet-500'
      )}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {/* Brain icon */}
      <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z" />
      <path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z" />
      <path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4" />
      <path d="M17.599 6.5a3 3 0 0 0 .399-1.375" />
      <path d="M6.003 5.125A3 3 0 0 0 6.401 6.5" />
      <path d="M3.477 10.896a4 4 0 0 1 .585-.396" />
      <path d="M19.938 10.5a4 4 0 0 1 .585.396" />
      <path d="M6 18a4 4 0 0 1-1.967-.516" />
      <path d="M19.967 17.484A4 4 0 0 1 18 18" />
    </svg>
  );
}

// Chevron icon for expand/collapse
function ChevronIcon({ isOpen }: { isOpen: boolean }) {
  return (
    <svg
      className={cn(
        'w-4 h-4 transition-transform duration-200',
        isOpen && 'rotate-180'
      )}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

// CopyIcon and CheckIcon are now imported from lucide-react

export function ReasoningBlock({
  title,
  thinking,
  messageId,
  isStreaming = false,
  compact = false,
  className,
  persona,
}: ReasoningBlockProps) {
  // Get persona-specific info
  const PersonaIcon = getPersonaIcon(persona);
  const personaName = getPersonaDisplayName(persona);
  const displayTitle = title || `${personaName} pensando`;
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const contentRef = useRef<HTMLDivElement>(null);

  // Auto-expand when streaming starts
  useEffect(() => {
    if (isStreaming && thinking.length > 0) {
      setIsOpen(true);
    }
  }, [isStreaming, thinking.length]);

  // Persistence by messageId
  useEffect(() => {
    if (!messageId) return;
    try {
      const key = `fi:thinking:open:${messageId}`;
      const saved = localStorage.getItem(key);
      if (saved != null) setIsOpen(saved === '1');
    } catch {
      // Ignore storage errors
    }
  }, [messageId]);

  useEffect(() => {
    if (!messageId) return;
    try {
      const key = `fi:thinking:open:${messageId}`;
      localStorage.setItem(key, isOpen ? '1' : '0');
    } catch {
      // Ignore storage errors
    }
  }, [isOpen, messageId]);

  // Auto-scroll when streaming
  useEffect(() => {
    if (isStreaming && isOpen && contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [thinking, isStreaming, isOpen]);

  // Copy handler
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(thinking);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Ignore copy errors
    }
  };

  // Word count for display
  const wordCount = thinking.trim().split(/\s+/).filter(Boolean).length;
  const preview = thinking.slice(0, 50);
  const hasMore = thinking.length > 50;

  if (compact) {
    return (
      <button
        type="button"
        onClick={() => setIsOpen(prev => !prev)}
        className={cn(
          'chat-think-compact-btn',
          className
        )}
        aria-expanded={isOpen}
        aria-label={`${displayTitle}: ${wordCount} palabras`}
      >
        <PersonaIcon className="w-3.5 h-3.5 text-emerald-500" />
        <span>{wordCount} palabras</span>
      </button>
    );
  }

  return (
    <div
      className={cn(
        'chat-think-container',
        isStreaming && 'chat-think-container-streaming',
        className
      )}
      role="region"
      aria-label={title}
    >
      {/* Header */}
      <button
        type="button"
        onClick={() => setIsOpen(prev => !prev)}
        className="chat-think-header-btn"
        aria-expanded={isOpen}
      >
        <div className="chat-think-header-left">
          {/* Persona Avatar - larger and more prominent */}
          <div className={cn(
            'chat-think-avatar',
            isStreaming && 'animate-pulse'
          )}>
            <PersonaIcon className="chat-think-avatar-icon" />
          </div>

          {/* Persona Name + Status */}
          <div className="chat-think-name-group">
            <span className="chat-think-persona-name">
              {personaName}
            </span>
            <span className={cn(
              'chat-think-status-badge',
              isStreaming && 'animate-pulse'
            )}>
              pensando...
            </span>
          </div>

          {isStreaming && (
            <span className="chat-think-live-badge">
              <span className="chat-think-live-dot" />
              <span>En vivo</span>
            </span>
          )}
        </div>

        <div className="fi-flex-gap-md">
          <span className="chat-think-wordcount">
            {wordCount} palabras
          </span>
          <ChevronIcon isOpen={isOpen} />
        </div>
      </button>

      {/* Collapsed Preview */}
      {!isOpen && thinking.length > 0 && (
        <div className="chat-think-preview">
          <p className="chat-think-preview-text">
            &quot;{preview}{hasMore && '...'}&quot;
          </p>
        </div>
      )}

      {/* Expanded Content */}
      <div
        className={cn(
          'chat-think-expand-transition',
          isOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
        )}
      >
        <div className="chat-think-divider" />

        <div
          ref={contentRef}
          className="chat-think-content-scroll"
        >
          {/* Content with improved typography */}
          <div
            className="chat-think-content-text"
          >
            {thinking}
            {isStreaming && (
              <span className="chat-think-cursor" />
            )}
          </div>

          {/* Fade gradient at bottom when content is long */}
          <div className="chat-think-fade" />
        </div>

        {/* Footer Actions */}
        <div className="chat-think-footer">
          <Button
            onClick={handleCopy}
            disabled={isStreaming}
            variant="ghost"
            size="sm"
            icon={copied ? Check : Copy}
            className={cn(
              'chat-think-copy-btn',
              copied && 'chat-think-copy-btn-copied'
            )}
          >
            {copied ? 'Copiado' : 'Copiar'}
          </Button>
        </div>
      </div>
    </div>
  );
}

/**
 * ThinkingIndicator - Animated indicator while AI is thinking
 *
 * Shows "Pensando..." with animated dots
 */
export function ThinkingIndicator({
  label = 'Pensando',
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'chat-think-indicator',
        className
      )}
      role="status"
      aria-live="polite"
    >
      <ThinkingIcon isAnimating />
      <span className="chat-think-indicator-label">
        {label}
      </span>
      <span className="flex gap-1" aria-hidden="true">
        {[0, 1, 2].map(i => (
          <span
            key={i}
            className="chat-think-bounce-dot"
            style={{ animationDelay: `${i * 150}ms` }}
          />
        ))}
      </span>
    </div>
  );
}

export default ReasoningBlock;
