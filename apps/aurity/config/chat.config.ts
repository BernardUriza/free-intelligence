/**
 * Chat Widget Configuration
 *
 * Centralized configuration for reusable chat components
 * Supports theming, behavior customization, and persona styling
 */

import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  Home,
  MessageCircle,
  BarChart3,
  FileText,
  Hand,
  Building2,
  Settings,
  Bot,
} from 'lucide-react';

// ============================================================================
// THEME CONFIGURATION
// ============================================================================

export interface ChatTheme {
  /** Widget background colors */
  background: {
    header: string;
    body: string;
    input: string;
  };

  /** Border colors */
  border: {
    main: string;
    input: string;
    bubble: string;
  };

  /** Text colors */
  text: {
    primary: string;
    secondary: string;
    muted: string;
    accent: string;
  };

  /** Accent gradient (for buttons, highlights) */
  accent: {
    from: string;
    to: string;
  };

  /** Shadow colors */
  shadow: string;

  /** Timestamp colors */
  timestamp: {
    text: string;
    tooltip: string;
  };
}

export const defaultTheme: ChatTheme = {
  background: {
    header: 'bg-gradient-to-r from-emerald-600 to-cyan-600',
    body: 'bg-slate-950',
    input: 'bg-slate-800',
  },
  border: {
    main: 'border-slate-700',
    input: 'border-slate-700',
    bubble: 'border-slate-600/60',
  },
  text: {
    primary: 'text-white',
    secondary: 'text-slate-200',
    muted: 'text-slate-400',
    accent: 'text-emerald-300',
  },
  accent: {
    from: 'from-emerald-600',
    to: 'to-cyan-600',
  },
  shadow: 'shadow-2xl',
  timestamp: {
    text: 'text-slate-400/70',
    tooltip: 'bg-slate-800/95 text-slate-200',
  },
};

// ============================================================================
// PERSONA CONFIGURATION
// ============================================================================

export interface PersonaStyle {
  /** Border color class */
  border: string;

  /** Background color class */
  bg: string;

  /** Shadow glow class */
  glow: string;

  /** Icon component (Lucide) or ReactNode for custom icons */
  icon: LucideIcon | ReactNode;

  /** Display label */
  label: string;

  /** Label color class */
  labelColor: string;

  /** Optional custom badge */
  badge?: {
    text: string;
    bg: string;
    textColor: string;
  };
}

export const personaStyles: Record<string, PersonaStyle> = {
  // Onboarding Guide - Sovereignty theme (emerald)
  onboarding_guide: {
    border: 'border-emerald-600/60',
    bg: 'bg-emerald-950/20',
    glow: 'shadow-emerald-500/10',
    icon: Home,
    label: 'FREE-INTELLIGENCE',
    labelColor: 'text-emerald-300',
  },

  // General Assistant - Neutral theme (slate)
  general_assistant: {
    border: 'border-slate-600/60',
    bg: 'bg-slate-900/20',
    glow: 'shadow-slate-500/10',
    icon: MessageCircle,
    label: 'FREE-INTELLIGENCE',
    labelColor: 'text-slate-300',
  },

  // Clinical Advisor - Evidence-based theme (blue)
  clinical_advisor: {
    border: 'border-blue-600/60',
    bg: 'bg-blue-950/20',
    glow: 'shadow-blue-500/10',
    icon: BarChart3,
    label: 'FREE-INTELLIGENCE · CLINICAL',
    labelColor: 'text-blue-300',
  },

  // SOAP Editor - Precision theme (cyan)
  soap_editor: {
    border: 'border-cyan-600/60',
    bg: 'bg-cyan-950/20',
    glow: 'shadow-cyan-500/10',
    icon: FileText,
    label: 'FREE-INTELLIGENCE · SOAP',
    labelColor: 'text-cyan-300',
  },

  // Waiting Room Host - Welcoming theme (purple)
  waiting_room_host: {
    border: 'border-purple-600/60',
    bg: 'bg-purple-950/20',
    glow: 'shadow-purple-500/10',
    icon: Hand,
    label: 'FREE-INTELLIGENCE · SALA DE ESPERA',
    labelColor: 'text-purple-300',
  },

  // FI Receptionist - Patient check-in assistant (indigo)
  fi_receptionist: {
    border: 'border-indigo-600/60',
    bg: 'bg-indigo-950/20',
    glow: 'shadow-indigo-500/10',
    icon: Building2,
    label: 'FI RECEPTIONIST',
    labelColor: 'text-indigo-300',
    badge: {
      text: 'CHECK-IN',
      bg: 'bg-indigo-500/20',
      textColor: 'text-indigo-400',
    },
  },

  // System Messages - Technical theme (amber)
  system: {
    border: 'border-amber-600/60',
    bg: 'bg-amber-950/20',
    glow: 'shadow-amber-500/10',
    icon: Settings,
    label: 'SYSTEM',
    labelColor: 'text-amber-300',
    badge: {
      text: 'INFO',
      bg: 'bg-amber-500/20',
      textColor: 'text-amber-400',
    },
  },
};

export const fallbackPersonaStyle: PersonaStyle = {
  border: 'border-slate-600/60',
  bg: 'bg-slate-900/20',
  glow: 'shadow-slate-500/10',
  icon: Bot,
  label: 'FREE-INTELLIGENCE',
  labelColor: 'text-slate-300',
};

// ============================================================================
// BEHAVIOR CONFIGURATION
// ============================================================================

export interface ChatBehavior {
  /** Auto-scroll to bottom on new messages */
  autoScroll: boolean;

  /** Show typing indicator */
  showTyping: boolean;

  /** Enable message grouping (hide redundant timestamps) */
  groupMessages: boolean;

  /** Threshold in minutes to group messages */
  groupThresholdMinutes: number;

  /** Show day dividers (e.g., "Hoy", "Ayer") */
  showDayDividers: boolean;

  /** Enable entrance animations */
  animateEntrance: boolean;

  /** Max messages to keep in memory */
  maxMessages: number;

  /** Placeholder text */
  inputPlaceholder: string;

  /** Send button label */
  sendButtonLabel?: string;

  /** Enable message reactions */
  enableReactions: boolean;

  /** Enable read receipts */
  enableReadReceipts: boolean;

  /** Request thinking/reasoning from model (Qwen3). Disabling saves compute. */
  enableThinking: boolean;

  /** Show thinking/reasoning UI (collapsible block). Independent of enableThinking. */
  showThinking: boolean;
}

export const defaultBehavior: ChatBehavior = {
  autoScroll: true,
  showTyping: true,
  groupMessages: true,
  groupThresholdMinutes: 2,
  showDayDividers: true,
  animateEntrance: true,
  maxMessages: 100,
  inputPlaceholder: 'Escribe tu mensaje...',
  enableReactions: false,
  enableReadReceipts: false,
  enableThinking: true, // Request thinking from model (can be disabled to save compute)
  showThinking: true, // Show thinking UI (can be hidden independently)
};

// ============================================================================
// TIMESTAMP CONFIGURATION
// ============================================================================

export interface TimestampConfig {
  /** Show timestamps by default */
  show: boolean;

  /** Format: 'relative' | 'absolute' | 'smart' */
  format: 'relative' | 'absolute' | 'smart';

  /** Show tooltip with absolute time */
  showTooltip: boolean;

  /** Threshold in minutes to switch from relative to absolute */
  relativeThreshold: number;

  /** Show seconds */
  showSeconds: boolean;

  /** Position: 'top' | 'bottom' | 'inline' */
  position: 'top' | 'bottom' | 'inline';

  /** Update interval in ms (for real-time relative updates) */
  updateInterval?: number;
}

export const defaultTimestampConfig: TimestampConfig = {
  show: true,
  format: 'smart',
  showTooltip: true,
  relativeThreshold: 60,
  showSeconds: false,
  position: 'inline',
  updateInterval: 60000, // Update every minute
};

// ============================================================================
// ANIMATION CONFIGURATION
// ============================================================================

export interface AnimationConfig {
  /** Message entrance animation */
  entrance: {
    enabled: boolean;
    duration: string; // e.g., '0.4s'
    easing: string; // e.g., 'ease-out'
  };

  /** Typing indicator animation */
  typing: {
    dotDuration: string;
    dotDelay: string;
  };

  /** Scroll behavior */
  scroll: {
    behavior: 'smooth' | 'auto';
    duration: number; // ms
  };
}

export const defaultAnimationConfig: AnimationConfig = {
  entrance: {
    enabled: true,
    duration: '0.4s',
    easing: 'ease-out',
  },
  typing: {
    dotDuration: '1.4s',
    dotDelay: '0.2s',
  },
  scroll: {
    behavior: 'smooth',
    duration: 300,
  },
};

// ============================================================================
// COMPLETE CHAT CONFIGURATION
// ============================================================================

export interface ChatConfig {
  /** Widget title */
  title: string;

  /** Widget subtitle */
  subtitle?: string;

  /** Theme configuration */
  theme: ChatTheme;

  /** Behavior configuration */
  behavior: ChatBehavior;

  /** Timestamp configuration */
  timestamp: TimestampConfig;

  /** Animation configuration */
  animation: AnimationConfig;

  /** Footer text */
  footer?: string;

  /** Widget dimensions */
  dimensions?: {
    width: string;
    height: string;
    minHeight?: string;
    maxHeight?: string;
  };
}

export const defaultChatConfig: ChatConfig = {
  title: 'Free Intelligence',
  subtitle: 'Tu asistente médico residente',
  theme: defaultTheme,
  behavior: defaultBehavior,
  timestamp: defaultTimestampConfig,
  animation: defaultAnimationConfig,
  footer: undefined, // Removed - model info shown in ModelBadge instead
  dimensions: {
    width: '24rem', // w-96
    height: '600px',
    minHeight: '400px',
    maxHeight: '80vh',
  },
};

// ============================================================================
// PRESET CONFIGURATIONS
// ============================================================================

/**
 * Minimal chat configuration (no animations, basic features)
 */
export const minimalChatConfig: ChatConfig = {
  ...defaultChatConfig,
  theme: defaultTheme,
  behavior: {
    ...defaultBehavior,
    groupMessages: false,
    showDayDividers: false,
    animateEntrance: false,
    enableReactions: false,
    enableReadReceipts: false,
  },
  timestamp: {
    ...defaultTimestampConfig,
    format: 'absolute',
    showTooltip: false,
  },
  animation: {
    ...defaultAnimationConfig,
    entrance: {
      ...defaultAnimationConfig.entrance,
      enabled: false,
    },
  },
};

/**
 * Clinical chat configuration (professional, minimal distractions)
 */
export const clinicalChatConfig: ChatConfig = {
  ...defaultChatConfig,
  title: 'Clinical Assistant',
  subtitle: 'Evidence-based medical guidance',
  theme: {
    ...defaultTheme,
    background: {
      header: 'bg-gradient-to-r from-blue-700 to-cyan-700',
      body: 'bg-slate-950',
      input: 'bg-slate-800',
    },
    accent: {
      from: 'from-blue-600',
      to: 'to-cyan-600',
    },
  },
  footer: 'HIPAA Compliant · AES-256 Encrypted',
};

/**
 * FI Receptionist configuration (patient check-in flow)
 * Used in waiting room QR check-in and kiosk mode
 */
export const receptionistChatConfig: ChatConfig = {
  ...defaultChatConfig,
  title: 'FI Receptionist',
  subtitle: 'Tu asistente de check-in',
  theme: {
    ...defaultTheme,
    background: {
      header: 'bg-gradient-to-r from-indigo-700 to-purple-700',
      body: 'bg-slate-950',
      input: 'bg-slate-800',
    },
    accent: {
      from: 'from-indigo-600',
      to: 'to-purple-600',
    },
    text: {
      ...defaultTheme.text,
      accent: 'text-indigo-300',
    },
  },
  behavior: {
    ...defaultBehavior,
    inputPlaceholder: '¿En qué puedo ayudarte?',
    groupMessages: true,
    showDayDividers: false, // Single session, no need for day dividers
  },
  footer: '100% Local · Datos protegidos',
  dimensions: {
    width: '100%',
    height: '100%',
    minHeight: '300px',
    maxHeight: '100vh',
  },
};

// ============================================================================
// RESPONSIVE BREAKPOINTS
// ============================================================================

/**
 * Mobile-first breakpoints for responsive chat widget
 *
 * Layout behavior:
 * - Mobile (<640px): Fullscreen overlay, entire viewport
 * - Tablet (640-1024px): Modal dialog, 90% viewport width
 * - Desktop (>1024px): Fixed widget, 384×600px bottom-right
 *
 * The .98px offset avoids edge-case rounding issues where
 * both (max-width: 640px) and (min-width: 640px) might match
 * simultaneously due to floating-point precision.
 */
export interface ChatBreakpoints {
  mobile: string;
  tablet: string;
  desktop: string;
}

export const CHAT_BREAKPOINTS: ChatBreakpoints = {
  mobile: '(max-width: 639.98px)',
  tablet: '(min-width: 640px) and (max-width: 1023.98px)',
  desktop: '(min-width: 1024px)',
};
