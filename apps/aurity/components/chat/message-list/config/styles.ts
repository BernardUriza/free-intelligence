/**
 * Message List Style Configuration
 *
 * Dense style inspired by Claude.ai / ChatGPT
 * - No bubbles, text is protagonist
 * - Minimal spacing
 * - Subtle avatars
 * - Dark grey (#121212) base
 */

export const messageStyles = {
  // Container
  container: {
    base: 'space-y-0.5',
    padding: 'px-4',
  },

  // Message row
  message: {
    base: 'group relative py-3 px-4 -mx-4 transition-colors duration-150',
    user: 'bg-transparent hover:bg-white/[0.02]',
    assistant: 'bg-white/[0.02] hover:bg-white/[0.04]',
    borderRadius: 'rounded-lg',
  },

  // Avatar
  avatar: {
    size: 'w-6 h-6',
    base: 'rounded-md flex items-center justify-center text-[10px] font-semibold flex-shrink-0',
    user: 'bg-violet-600/80 text-white',
    assistant: 'bg-amber-500/80 text-slate-900',
  },

  // Meta (name + time)
  meta: {
    container: 'flex items-baseline gap-2',
    name: 'text-[13px] font-medium text-slate-300',
    time: 'text-[11px] text-slate-500 tabular-nums',
  },

  // Content
  content: {
    base: 'text-[14px] leading-relaxed',
    user: 'text-slate-200',
    assistant: 'text-slate-100',
    indent: 'pl-8', // Align with avatar
  },

  // Actions toolbar
  actions: {
    container: `
      absolute top-2 right-2
      flex items-center gap-0.5
      opacity-0 group-hover:opacity-100
      transition-opacity duration-150
      bg-slate-800/95 backdrop-blur-sm rounded-md p-0.5
      border border-slate-700/50 shadow-lg
    `,
    button: {
      base: 'p-1 rounded transition-colors duration-150',
      idle: 'hover:bg-slate-700 text-slate-400 hover:text-slate-200',
      active: 'bg-emerald-500/20 text-emerald-400',
      speaking: 'bg-amber-500/20 text-amber-400',
    },
    icon: 'w-3 h-3',
  },

  // Date divider
  dateDivider: {
    container: 'my-4 flex items-center gap-3',
    line: 'flex-1 h-px bg-gradient-to-r from-transparent via-slate-700/30 to-transparent',
    label: 'px-3 py-1 text-[10px] text-slate-500 font-medium bg-slate-900/50 rounded-full',
  },

  // Typing indicator
  typing: {
    container: 'flex items-center gap-2 px-4 py-2',
    dot: 'w-1.5 h-1.5 bg-amber-400/80 rounded-full',
    animation: 'animate-bounce',
  },
} as const;

// Markdown component styles
export const markdownStyles = {
  p: 'mb-3 last:mb-0',
  strong: 'font-semibold text-white',
  em: 'italic text-slate-300',
  code: 'px-1 py-0.5 bg-slate-800/80 rounded text-amber-300/90 font-mono text-[13px]',
  pre: 'my-3 p-3 bg-slate-900/80 rounded-lg border border-slate-700/30 overflow-x-auto text-[13px]',
  ul: 'my-2 ml-0.5 space-y-1.5',
  ol: 'my-2 ml-0.5 space-y-1.5 list-decimal list-inside',
  li: 'flex gap-1.5 text-slate-200',
  bullet: 'text-slate-500 select-none text-[10px] mt-1',
  h1: 'text-lg font-semibold text-white mt-4 mb-2',
  h2: 'text-base font-semibold text-white mt-3 mb-1.5',
  h3: 'text-sm font-semibold text-slate-100 mt-2 mb-1',
  blockquote: 'my-3 pl-3 border-l-2 border-slate-600/50 text-slate-400 italic text-[13px]',
  link: 'text-amber-400/90 hover:text-amber-300 underline underline-offset-2 transition-colors',
} as const;
