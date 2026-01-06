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
import type { FITone } from '@aurity-standalone/types/assistant';
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
function getPersonaDisplayName(persona?: FITone): string {
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
  persona?: FITone;
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
          'inline-flex items-center gap-1.5 px-2 py-1 text-xs rounded-full',
          'bg-violet-50 dark:bg-violet-950/40 text-violet-700 dark:text-violet-300',
          'hover:bg-violet-100 dark:hover:bg-violet-900/50 transition-colors',
          'border border-violet-200 dark:border-violet-800',
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
        'w-full rounded-xl overflow-hidden transition-all duration-300',
        'border border-violet-200/60 dark:border-violet-800/50',
        'border-l-4 border-l-violet-400 dark:border-l-violet-500', // Accent border
        'bg-gradient-to-br from-violet-50/90 via-slate-50 to-fuchsia-50/60',
        'dark:from-violet-950/50 dark:via-slate-900/80 dark:to-fuchsia-950/40',
        'shadow-sm hover:shadow-md',
        isStreaming && 'ring-2 ring-violet-400/40 dark:ring-violet-500/30 shadow-violet-500/10 shadow-lg',
        className
      )}
      role="region"
      aria-label={title}
    >
      {/* Header */}
      <button
        type="button"
        onClick={() => setIsOpen(prev => !prev)}
        className={cn(
          'w-full flex items-center justify-between gap-3 px-4 py-3.5',
          'bg-gradient-to-r from-violet-100/60 via-transparent to-fuchsia-100/40',
          'dark:from-violet-900/40 dark:via-transparent dark:to-fuchsia-900/30',
          'hover:from-violet-100 hover:to-fuchsia-100/60',
          'dark:hover:from-violet-900/60 dark:hover:to-fuchsia-900/40',
          'transition-all duration-200',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-inset'
        )}
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-3 min-w-0">
          {/* Persona Avatar - larger and more prominent */}
          <div className={cn(
            'flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center',
            'bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20',
            'border border-violet-400/40 dark:border-violet-500/40',
            isStreaming && 'animate-pulse'
          )}>
            <PersonaIcon className="w-4 h-4 text-violet-600 dark:text-violet-400" />
          </div>

          {/* Persona Name + Status */}
          <div className="flex items-center gap-2 min-w-0">
            <span className="font-semibold text-sm text-violet-800 dark:text-violet-200">
              {personaName}
            </span>
            <span className={cn(
              'fi-text-xs-medium px-2 py-0.5 rounded-full',
              'bg-violet-200/60 dark:bg-violet-800/40',
              'text-violet-700 dark:text-violet-300',
              isStreaming && 'animate-pulse'
            )}>
              pensando...
            </span>
          </div>

          {isStreaming && (
            <span className="flex items-center gap-1.5 fi-text-xs-medium text-violet-600 dark:text-violet-400 bg-violet-200/50 dark:bg-violet-800/30 px-2 py-0.5 rounded-full">
              <span className="w-2 h-2 rounded-full bg-violet-500 animate-ping" />
              <span>En vivo</span>
            </span>
          )}
        </div>

        <div className="fi-flex-gap-md">
          <span className="fi-text-xs-medium text-violet-600/80 dark:text-violet-400/80 tabular-nums bg-violet-100/60 dark:bg-violet-900/40 px-2 py-0.5 rounded">
            {wordCount} palabras
          </span>
          <ChevronIcon isOpen={isOpen} />
        </div>
      </button>

      {/* Collapsed Preview */}
      {!isOpen && thinking.length > 0 && (
        <div className="px-4 pb-3 -mt-1">
          <p className="text-xs text-violet-700/60 dark:text-violet-300/50 line-clamp-1 italic">
            &quot;{preview}{hasMore && '...'}&quot;
          </p>
        </div>
      )}

      {/* Expanded Content */}
      <div
        className={cn(
          'overflow-hidden transition-all duration-300 ease-in-out',
          isOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
        )}
      >
        <div className="border-t border-violet-200/40 dark:border-violet-800/30" />

        <div
          ref={contentRef}
          className={cn(
            'px-4 py-4 overflow-y-auto max-h-80',
            'relative reasoning-scrollbar'
          )}
        >
          {/* Content with improved typography */}
          <div
            className={cn(
              'text-[13px] leading-[1.7] whitespace-pre-wrap',
              'font-[ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace]',
              'text-violet-900/85 dark:text-violet-100/85',
              'selection:bg-violet-200 dark:selection:bg-violet-700',
              // Paragraph-like spacing for readability
              '[&]:space-y-2'
            )}
          >
            {thinking}
            {isStreaming && (
              <span className="inline-block w-2 h-4 ml-1 bg-violet-500 animate-pulse rounded-sm align-middle" />
            )}
          </div>

          {/* Fade gradient at bottom when content is long */}
          <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-violet-50/90 dark:from-slate-900/90 to-transparent pointer-events-none" />
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-2 px-4 py-2 border-t border-violet-200/40 dark:border-violet-800/30 bg-violet-50/50 dark:bg-violet-950/30">
          <Button
            onClick={handleCopy}
            disabled={isStreaming}
            variant="ghost"
            size="sm"
            icon={copied ? Check : Copy}
            className={cn(
              'text-violet-700 dark:text-violet-300',
              'hover:bg-violet-200/60 dark:hover:bg-violet-800/40',
              copied && 'text-green-500'
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
        'inline-flex items-center gap-2 px-3 py-2 rounded-xl',
        'bg-gradient-to-r from-violet-100 to-fuchsia-100',
        'dark:from-violet-900/40 dark:to-fuchsia-900/40',
        'border border-violet-200/50 dark:border-violet-700/50',
        className
      )}
      role="status"
      aria-live="polite"
    >
      <ThinkingIcon isAnimating />
      <span className="text-sm text-violet-800 dark:text-violet-200">
        {label}
      </span>
      <span className="flex gap-1" aria-hidden="true">
        {[0, 1, 2].map(i => (
          <span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-violet-500 animate-bounce"
            style={{ animationDelay: `${i * 150}ms` }}
          />
        ))}
      </span>
    </div>
  );
}

export default ReasoningBlock;
