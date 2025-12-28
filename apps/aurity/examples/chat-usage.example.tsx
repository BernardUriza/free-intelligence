/**
 * Chat Widget Usage Examples
 *
 * This file demonstrates how to use the enhanced configurable ChatWidget
 * with custom themes, timestamps, and behavior settings.
 */

import { ChatWidget } from '@/components/chat/ChatWidget';
import {
  minimalChatConfig,
  clinicalChatConfig,
} from '@/config/chat.config';

// ============================================================================
// EXAMPLE 1: Default Configuration (no props needed)
// ============================================================================

export function DefaultChatExample() {
  return <ChatWidget />;
}

// ============================================================================
// EXAMPLE 2: Clinical Professional Theme
// ============================================================================

export function ClinicalChatExample() {
  return <ChatWidget config={clinicalChatConfig} />;
}

// ============================================================================
// EXAMPLE 3: Minimal Chat (no animations, basic timestamps)
// ============================================================================

export function MinimalChatExample() {
  return <ChatWidget config={minimalChatConfig} />;
}

// ============================================================================
// EXAMPLE 4: Custom Configuration (partial override)
// ============================================================================

export function CustomChatExample() {
  return (
    <ChatWidget
      config={{
        title: 'Asistente Personalizado',
        subtitle: 'Siempre aquí para ayudarte',
        theme: {
          accent: {
            from: 'from-emerald-600',
            to: 'to-cyan-600',
          },
        },
        timestamp: {
          show: true,
          format: 'relative', // 'relative' | 'absolute' | 'smart'
          showTooltip: true,
          updateInterval: 30000, // Update every 30s
        },
        behavior: {
          autoScroll: true,
          groupMessages: true,
          showDayDividers: true,
          animateEntrance: true,
          inputPlaceholder: 'Pregúntame algo...',
        },
      }}
    />
  );
}

// ============================================================================
// EXAMPLE 5: Advanced Custom Theme
// ============================================================================

export function AdvancedThemeChatExample() {
  return (
    <ChatWidget
      config={{
        title: 'Emergency Assistant',
        subtitle: 'Rapid Response System',
        theme: {
          background: {
            header: 'bg-gradient-to-r from-red-700 to-orange-700',
            body: 'bg-slate-950',
            input: 'bg-slate-800',
          },
          accent: {
            from: 'from-red-600',
            to: 'to-orange-600',
          },
          timestamp: {
            text: 'fi-text-error/70',
            tooltip: 'bg-red-900/95 text-red-100',
          },
        },
        footer: 'Emergency Protocol Active · 24/7 Response',
      }}
    />
  );
}

// ============================================================================
// EXAMPLE 6: Timestamp Configuration Examples
// ============================================================================

// Show absolute time only (no relative "hace 2min")
export function AbsoluteTimestampChat() {
  return (
    <ChatWidget
      config={{
        timestamp: {
          show: true,
          format: 'absolute',
          showTooltip: false,
        },
      }}
    />
  );
}

// Smart timestamps with custom threshold
export function SmartTimestampChat() {
  return (
    <ChatWidget
      config={{
        timestamp: {
          show: true,
          format: 'smart',
          relativeThreshold: 120, // Switch to absolute after 2 hours
          showSeconds: true,
          updateInterval: 15000, // Update every 15s
        },
      }}
    />
  );
}

// ============================================================================
// EXAMPLE 7: Behavior Customization
// ============================================================================

// Disable message grouping and day dividers
export function SimpleBehaviorChat() {
  return (
    <ChatWidget
      config={{
        behavior: {
          autoScroll: true,
          showTyping: true,
          groupMessages: false, // Show timestamp on every message
          showDayDividers: false, // No "Hoy", "Ayer" dividers
          animateEntrance: false,
          maxMessages: 50,
          inputPlaceholder: 'Type here...',
          enableReactions: false,
          enableReadReceipts: false,
        },
      }}
    />
  );
}

// ============================================================================
// EXAMPLE 8: Compact Chat for Small Screens
// ============================================================================

export function CompactChatExample() {
  return (
    <ChatWidget
      config={{
        title: 'FI',
        subtitle: undefined, // No subtitle
        dimensions: {
          width: '20rem', // Narrower
          height: '400px', // Shorter
        },
        timestamp: {
          show: false, // Hide timestamps for more space
        },
        footer: undefined, // No footer
      }}
    />
  );
}

// ============================================================================
// USAGE IN LAYOUT OR PAGE
// ============================================================================

/**
 * Example: Add to your main layout
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        {children}

        {/* Default Chat Widget (bottom-right corner) */}
        <ChatWidget />

        {/* OR with custom config */}
        {/* <ChatWidget config={clinicalChatConfig} /> */}
      </body>
    </html>
  );
}

// ============================================================================
// CONFIGURATION REFERENCE
// ============================================================================

/**
 * ChatConfig Interface:
 *
 * {
 *   title: string;
 *   subtitle?: string;
 *   theme: {
 *     background: { header, body, input }
 *     border: { main, input, bubble }
 *     text: { primary, secondary, muted, accent }
 *     accent: { from, to }
 *     shadow: string
 *     timestamp: { text, tooltip }
 *   }
 *   behavior: {
 *     autoScroll: boolean
 *     showTyping: boolean
 *     groupMessages: boolean
 *     groupThresholdMinutes: number
 *     showDayDividers: boolean
 *     animateEntrance: boolean
 *     maxMessages: number
 *     inputPlaceholder: string
 *     enableReactions: boolean
 *     enableReadReceipts: boolean
 *   }
 *   timestamp: {
 *     show: boolean
 *     format: 'relative' | 'absolute' | 'smart'
 *     showTooltip: boolean
 *     relativeThreshold: number
 *     showSeconds: boolean
 *     position: 'top' | 'bottom' | 'inline'
 *     updateInterval?: number
 *   }
 *   animation: {
 *     entrance: { enabled, duration, easing }
 *     typing: { dotDuration, dotDelay }
 *     scroll: { behavior, duration }
 *   }
 *   footer?: string
 *   dimensions?: {
 *     width: string
 *     height: string
 *     minHeight?: string
 *     maxHeight?: string
 *   }
 * }
 */
