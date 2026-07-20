/**
 * fi-glass · shell config — the ChatConfig contract the shell renders against.
 *
 * Copied (shape-for-shape) from aurity's `config/chat.config.ts` so the app can
 * pass its own ChatConfig into <ChatWidget config={…}> with zero friction
 * (TypeScript checks structurally). The shell only ever reads `title`,
 * `subtitle`, `theme.background.header` and `behavior.showThinking`; the rest of
 * the shape is kept identical so the default is complete and the app's superset
 * stays assignable. Persona styles are NOT here — they belong to the message
 * render layer (aurity domain), not the shell skeleton.
 */

export interface ChatTheme {
  background: { header: string; body: string; input: string };
  border: { main: string; input: string; bubble: string };
  text: { primary: string; secondary: string; muted: string; accent: string };
  accent: { from: string; to: string };
  shadow: string;
  timestamp: { text: string; tooltip: string };
}

export interface ChatBehavior {
  autoScroll: boolean;
  showTyping: boolean;
  groupMessages: boolean;
  groupThresholdMinutes: number;
  showDayDividers: boolean;
  animateEntrance: boolean;
  maxMessages: number;
  inputPlaceholder: string;
  sendButtonLabel?: string;
  enableReactions: boolean;
  enableReadReceipts: boolean;
  enableThinking: boolean;
  showThinking: boolean;
}

export interface TimestampConfig {
  show: boolean;
  format: 'relative' | 'absolute' | 'smart';
  showTooltip: boolean;
  relativeThreshold: number;
  showSeconds: boolean;
  position: 'top' | 'bottom' | 'inline';
  updateInterval?: number;
}

export interface AnimationConfig {
  entrance: { enabled: boolean; duration: string; easing: string };
  typing: { dotDuration: string; dotDelay: string };
  scroll: { behavior: 'smooth' | 'auto'; duration: number };
}

export interface ChatConfig {
  title: string;
  subtitle?: string;
  theme: ChatTheme;
  behavior: ChatBehavior;
  timestamp: TimestampConfig;
  animation: AnimationConfig;
  footer?: string;
  dimensions?: { width: string; height: string; minHeight?: string; maxHeight?: string };
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
  accent: { from: 'from-emerald-600', to: 'to-cyan-600' },
  shadow: 'shadow-2xl',
  timestamp: {
    text: 'text-slate-400/70',
    tooltip: 'bg-slate-800/95 text-slate-200',
  },
};

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
  enableThinking: true,
  showThinking: true,
};

export const defaultTimestampConfig: TimestampConfig = {
  show: true,
  format: 'smart',
  showTooltip: true,
  relativeThreshold: 60,
  showSeconds: false,
  position: 'inline',
  updateInterval: 60000,
};

export const defaultAnimationConfig: AnimationConfig = {
  entrance: { enabled: true, duration: '0.4s', easing: 'ease-out' },
  typing: { dotDuration: '1.4s', dotDelay: '0.2s' },
  scroll: { behavior: 'smooth', duration: 300 },
};

/** Neutral default — apps inject their own ChatConfig and only fall back here. */
export const defaultChatConfig: ChatConfig = {
  title: 'Free Intelligence',
  subtitle: undefined,
  theme: defaultTheme,
  behavior: defaultBehavior,
  timestamp: defaultTimestampConfig,
  animation: defaultAnimationConfig,
  footer: undefined,
  dimensions: { width: '24rem', height: '600px', minHeight: '400px', maxHeight: '80vh' },
};

/** Merge a partial app config over the fi-glass default (one level deep on the nested groups). */
export function mergeChatConfig(custom?: Partial<ChatConfig>): ChatConfig {
  if (!custom) return defaultChatConfig;
  return {
    ...defaultChatConfig,
    ...custom,
    theme: { ...defaultChatConfig.theme, ...custom.theme },
    behavior: { ...defaultChatConfig.behavior, ...custom.behavior },
    timestamp: { ...defaultChatConfig.timestamp, ...custom.timestamp },
    animation: { ...defaultChatConfig.animation, ...custom.animation },
  };
}

// ---- Responsive breakpoints (was aurity CHAT_BREAKPOINTS) ----
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
