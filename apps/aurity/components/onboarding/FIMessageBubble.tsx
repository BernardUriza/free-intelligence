'use client';

/**
 * FIMessageBubble Component
 *
 * Card: FI-ONBOARD-002
 * Displays Free-Intelligence messages with persona-based styling
 * Enhanced with smart timestamps and tooltips
 */

import type { FIMessage } from '@aurity-standalone/types/assistant';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Stethoscope, FileEdit, Microscope, Compass, Network, Shield, TrendingUp, Activity } from 'lucide-react';
import { MessageTimestamp } from '@/components/chat/MessageTimestamp';
import { CopyButton, SpeakButton } from '@/components/chat/MessageActions';
import { ModelBadge } from '@/components/chat/message-list/ui/ModelBadge';
import type { TimestampConfig } from '@/config/chat.config';
import { usePersonas } from '@aurity-standalone/hooks/usePersonas';
import { useAudioPlayer } from '@/components/chat/AudioPlayer';

/**
 * Persona-based styling configuration
 * Maps backend personas to VISUAL themes ONLY
 *
 * NOTE: Labels are no longer hardcoded here.
 * Persona names come from backend dynamically.
 */
const PERSONA_STYLES = {
  // Onboarding Guide - Sovereignty theme (emerald)
  onboarding_guide: {
    border: 'border-emerald-600/60',
    bg: 'bg-emerald-950/20',
    glow: 'shadow-emerald-500/10',
    Icon: Compass,
    labelColor: 'text-emerald-300',
  },

  // General Assistant - Neutral theme (slate)
  general_assistant: {
    border: 'border-slate-600/60',
    bg: 'bg-slate-900/20',
    glow: 'shadow-slate-500/10',
    Icon: Stethoscope,
    labelColor: 'fi-text',
  },

  // Clinical Advisor - Evidence-based theme (blue)
  clinical_advisor: {
    border: 'border-blue-600/60',
    bg: 'bg-blue-950/20',
    glow: 'shadow-blue-500/10',
    Icon: Microscope,
    labelColor: 'text-blue-300',
  },

  // SOAP Editor - Precision theme (cyan)
  soap_editor: {
    border: 'border-cyan-600/60',
    bg: 'bg-cyan-950/20',
    glow: 'shadow-cyan-500/10',
    Icon: FileEdit,
    labelColor: 'text-cyan-300',
  },

  // Waiting Room Host - Welcoming theme (purple)
  waiting_room_host: {
    border: 'border-purple-600/60',
    bg: 'bg-purple-950/20',
    glow: 'shadow-purple-500/10',
    Icon: Compass,
    labelColor: 'text-purple-300',
  },

  // ==== PHILOSOPHICAL PERSONAS (Free Intelligence Core Principles) ====

  // Pattern Weaver - Memory archaeology theme (violet)
  pattern_weaver: {
    border: 'border-violet-600/60',
    bg: 'bg-violet-950/20',
    glow: 'shadow-violet-500/10',
    Icon: Network,
    labelColor: 'text-violet-300',
  },

  // Sovereignty Guide - Data sovereignty theme (amber)
  sovereignty_guide: {
    border: 'border-amber-600/60',
    bg: 'bg-amber-950/20',
    glow: 'shadow-amber-500/10',
    Icon: Shield,
    labelColor: 'text-amber-300',
  },

  // Growth Mirror - Symbiotic development theme (rose)
  growth_mirror: {
    border: 'border-rose-600/60',
    bg: 'bg-rose-950/20',
    glow: 'shadow-rose-500/10',
    Icon: TrendingUp,
    labelColor: 'text-rose-300',
  },

  // Honest Limiter - Anti-oracle theme (orange)
  honest_limiter: {
    border: 'border-orange-600/60',
    bg: 'bg-orange-950/20',
    glow: 'shadow-orange-500/10',
    Icon: Activity,
    labelColor: 'text-orange-300',
  },
} as const;

/**
 * Fallback style for unknown personas
 */
const FALLBACK_STYLE = {
  border: 'border-slate-600/60',
  bg: 'bg-slate-900/20',
  glow: 'shadow-slate-500/10',
  Icon: Stethoscope,
  labelColor: 'fi-text',
};

/**
 * Generate label from persona name (backend format → display format)
 * Examples:
 *   "General Assistant" → "FREE-INTELLIGENCE"
 *   "SOAP Editor" → "FREE-INTELLIGENCE · SOAP EDITOR"
 *   "Honest Limiter" → "FI · HONEST LIMITER"
 */
function generatePersonaLabel(personaName: string | undefined): string {
  if (!personaName) return 'FREE-INTELLIGENCE';

  // Philosophical personas use short "FI" prefix
  const philosophicalPersonas = ['Pattern Weaver', 'Sovereignty Guide', 'Growth Mirror', 'Honest Limiter'];
  const isPhilosophical = philosophicalPersonas.includes(personaName);

  if (personaName === 'General Assistant') {
    return 'FREE-INTELLIGENCE';
  }

  const prefix = isPhilosophical ? 'FI' : 'FREE-INTELLIGENCE';
  const suffix = personaName.toUpperCase();

  return `${prefix} · ${suffix}`;
}

export interface FIMessageBubbleProps {
  /** Message to display */
  message: FIMessage;

  /** Show timestamp */
  showTimestamp?: boolean;

  /** Show sender name (for first message in group) */
  showSenderName?: boolean;

  /** Timestamp configuration */
  timestampConfig?: Partial<TimestampConfig>;

  /** Animate entrance */
  animate?: boolean;

  /** Additional CSS classes */
  className?: string;

  /** Override border radius (for grouped messages) */
  borderRadiusOverride?: string;
}

/**
 * Message bubble for Free-Intelligence responses
 *
 * Features:
 * - Persona-based visual styling
 * - Neo-minimalist glassmorphism design
 * - Smooth entrance animations
 * - Accessible markup
 *
 * @example
 * ```tsx
 * <FIMessageBubble
 *   message={{
 *     role: 'assistant',
 *     content: 'Hola, soy Free-Intelligence...',
 *     timestamp: '2025-11-18T12:00:00Z',
 *     metadata: { tone: 'onboarding_guide', phase: 'welcome' }
 *   }}
 *   showTimestamp
 *   animate
 * />
 * ```
 */
export function FIMessageBubble({
  message,
  showTimestamp = true,
  showSenderName = true,
  timestampConfig,
  animate = true,
  className = '',
  borderRadiusOverride,
}: FIMessageBubbleProps) {
  // Use override or default border radius
  const borderRadius = borderRadiusOverride || 'rounded-2xl rounded-tl-sm';
  // Get persona from metadata (fallback to general_assistant)
  const persona = message.metadata?.tone || 'general_assistant';

  // Fetch personas to get real names and voices from backend
  const { personas } = usePersonas();

  // Get audio player for TTS
  const { generateAudio } = useAudioPlayer();

  // Get style for persona (with fallback)
  const style = PERSONA_STYLES[persona as keyof typeof PERSONA_STYLES] || FALLBACK_STYLE;

  // Get persona data from backend (single source of truth)
  const personaData = personas.find(p => p.id === persona);
  const personaLabel = generatePersonaLabel(personaData?.name);

  // Get voice for this persona (from backend config or message metadata)
  const personaVoice = message.metadata?.voice || personaData?.voice;

  return (
    <div
      className={`${animate ? 'fi-message-container-animated' : 'fi-message-container'} ${className}`}
      role="article"
      aria-label="Free-Intelligence message"
    >
      {/* Message Bubble (2026 design) */}
      <div
        className={`relative group flex-1 max-w-[72ch] px-3 py-1.5 ${borderRadius} border ${style.border.replace('/60', '/[0.12]')} ${style.bg.replace('/20', '/[0.06]')} backdrop-blur-2xl backdrop-saturate-150 shadow-sm shadow-black/5 transition-all duration-300 ease-out hover:shadow-md`}
      >
        {/* Message Content */}
        <div className="text-sm text-slate-100/95 leading-snug prose prose-invert max-w-none tracking-[-0.005em]">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // Compact headings
              h1: ({ children }) => (
                <h1 className="text-base font-[650] bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent mt-2 mb-1 leading-tight tracking-[-0.02em]">
                  {children}
                </h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-sm font-[600] text-emerald-300/95 mt-2 mb-1 leading-tight tracking-[-0.01em]">
                  {children}
                </h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-sm font-[500] text-emerald-200/90 mt-1 mb-0.5 flex items-center gap-1.5 tracking-[-0.005em]">
                  <span className="w-1 h-1 rounded-full bg-emerald-400/70 shadow-sm shadow-emerald-400/50"></span>
                  {children}
                </h3>
              ),

              // Text formatting
              strong: ({ children }) => (
                <strong className="font-semibold text-white">{children}</strong>
              ),
              em: ({ children }) => (
                <em className="italic fi-text">{children}</em>
              ),
              code: ({ children }) => (
                <code className="px-1.5 py-0.5 bg-emerald-950/40 border border-emerald-500/20 rounded text-emerald-300 font-mono text-[11px]">
                  {children}
                </code>
              ),

              // Links (compact)
              a: ({ href, children }) => (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="fi-text-info hover:text-cyan-300 underline decoration-cyan-500/50 hover:decoration-cyan-400 underline-offset-2 transition-colors text-sm"
                >
                  {children} ↗
                </a>
              ),

              // Lists (compact)
              ul: ({ children }) => (
                <ul className="list-none space-y-0.5 my-1.5">
                  {children}
                </ul>
              ),
              ol: ({ children }) => (
                <ol className="list-none space-y-0.5 my-1.5 counter-reset-[item]">
                  {children}
                </ol>
              ),
              li: ({ children }) => {
                const content = String(children);
                if (content.includes('[ ]')) {
                  return (
                    <li className="flex items-start gap-1.5 text-slate-200">
                      <span className="flex-shrink-0 w-3 h-3 mt-0.5 border border-slate-500/60 rounded" />
                      <span className="text-sm">{content.replace('[ ]', '').trim()}</span>
                    </li>
                  );
                }
                if (content.includes('[x]') || content.includes('[X]')) {
                  return (
                    <li className="flex items-start gap-1.5 text-slate-200">
                      <span className="flex-shrink-0 w-3 h-3 mt-0.5 bg-emerald-500/20 border border-emerald-500/60 rounded flex items-center justify-center">
                        <svg className="w-2 h-2 fi-text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </span>
                      <span className="text-sm">{content.replace(/\[x\]|\[X\]/i, '').trim()}</span>
                    </li>
                  );
                }
                return (
                  <li className="flex items-start gap-1.5 text-slate-200">
                    <span className="flex-shrink-0 w-1 h-1 mt-1.5 rounded-full bg-emerald-400" />
                    <span className="flex-1 text-sm">{children}</span>
                  </li>
                );
              },

              // Paragraphs (compact spacing)
              p: ({ children }) => (
                <p className="mb-1.5 last:mb-0 text-slate-200/95 leading-snug">
                  {children}
                </p>
              ),

              // Code blocks (compact)
              pre: ({ children }) => (
                <pre className="bg-slate-950/60 p-2 rounded-lg overflow-x-auto my-1.5 border border-emerald-500/10 font-mono text-xs leading-tight">
                  {children}
                </pre>
              ),

              // Horizontal rule
              hr: () => (
                <hr className="my-2 border-0 h-px bg-emerald-500/20" />
              ),

              // Blockquote (compact)
              blockquote: ({ children }) => (
                <blockquote className="border-l-2 border-emerald-500/50 pl-2 pr-2 py-1 my-1.5 italic fi-text/90 bg-emerald-950/10 rounded-r text-sm">
                  {children}
                </blockquote>
              ),

              // Tables (compact)
              table: ({ children }) => (
                <div className="overflow-x-auto my-1.5">
                  <table className="min-w-full border border-slate-700/50 rounded text-xs">
                    {children}
                  </table>
                </div>
              ),
              thead: ({ children }) => (
                <thead className="bg-slate-800/60">
                  {children}
                </thead>
              ),
              tbody: ({ children }) => (
                <tbody className="divide-y divide-slate-700/30">
                  {children}
                </tbody>
              ),
              tr: ({ children }) => (
                <tr className="hover:bg-slate-800/20 transition-colors">
                  {children}
                </tr>
              ),
              th: ({ children }) => (
                <th className="px-2 py-1 text-left text-[10px] font-semibold text-emerald-300 uppercase">
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td className="px-2 py-1 text-xs fi-text">
                  {children}
                </td>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Metadata footer (ultra-compact, single line) */}
        <div className="mt-1 flex items-center gap-2 justify-between text-[10px] text-slate-500">
          <div className="flex items-center gap-1.5">
            {showSenderName && personaLabel && (
              <>
                <span className={`font-medium ${style.labelColor}`}>
                  {personaLabel}
                </span>
                <span className="text-slate-600">•</span>
              </>
            )}
            {showTimestamp && (
              <MessageTimestamp
                timestamp={message.timestamp}
                config={timestampConfig}
                position="inline"
                size="xs"
              />
            )}
            {message.metadata?.phase && (
              <>
                <span className="text-slate-600">•</span>
                <span className="text-slate-500">{message.metadata.phase}</span>
              </>
            )}
          </div>

          {/* Action buttons (compact) + ModelBadge */}
          <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-2">
            <CopyButton content={message.content} size="sm" />
            <SpeakButton content={message.content} size="sm" voice={personaVoice} onOpenPlayer={generateAudio} />
            {personaVoice && (
              <ModelBadge model={personaData?.model || 'free-intelligence'} className="ml-1" voice={personaVoice} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


/**
 * Animation keyframes (add to global CSS or Tailwind config)
 *
 * @keyframes fade-in-up {
 *   from {
 *     opacity: 0;
 *     transform: translateY(10px);
 *   }
 *   to {
 *     opacity: 1;
 *     transform: translateY(0);
 *   }
 * }
 *
 * .animate-fade-in-up {
 *   animation: fade-in-up 0.4s ease-out;
 * }
 */
