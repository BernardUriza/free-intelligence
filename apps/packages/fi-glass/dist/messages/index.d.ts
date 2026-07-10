import * as react from 'react';
import { ReactNode } from 'react';

/**
 * fi-glass · message style configuration
 * Copied verbatim from aurity ui/message/styles/message-styles.ts on 2026-06-01
 * (Plutonio). Class strings are identical so rendering is unchanged.
 *
 * Dense style inspired by Claude.ai / ChatGPT:
 * - No bubbles, text is protagonist
 * - Minimal spacing, subtle avatars
 *
 * NOTE: values are duplicated with aurity's local copy during the migration —
 * known debt, same call as the theme tokens. Apps override per-instance via the
 * className props on each primitive, so they never need to touch this file.
 */
declare const messageStyles: {
    readonly container: {
        readonly base: "space-y-0.5";
        readonly padding: "px-4";
    };
    readonly message: {
        readonly base: "group relative py-3 px-4 -mx-4 transition-colors duration-150";
        readonly user: "bg-transparent hover:bg-white/[0.02]";
        readonly assistant: "bg-white/[0.02] hover:bg-white/[0.04]";
        readonly borderRadius: "rounded-lg";
    };
    readonly avatar: {
        readonly size: "w-6 h-6";
        readonly base: "rounded-md flex items-center justify-center text-[10px] font-semibold flex-shrink-0";
        readonly user: "bg-violet-600/80 text-white";
        readonly assistant: "bg-amber-500/80 text-slate-900";
    };
    readonly meta: {
        readonly container: "flex items-baseline gap-2";
        readonly name: "text-[13px] font-medium text-slate-300";
        readonly time: "text-[11px] text-slate-500 tabular-nums";
    };
    readonly content: {
        readonly base: "text-[14px] leading-relaxed";
        readonly user: "text-slate-200";
        readonly assistant: "text-slate-100";
        readonly indent: "pl-8";
    };
    readonly actions: {
        readonly container: "\n      absolute top-2 right-2\n      flex items-center gap-0.5\n      opacity-0 group-hover:opacity-100\n      transition-opacity duration-150\n      bg-slate-800/95 backdrop-blur-sm rounded-md p-0.5\n      border border-slate-700/50 shadow-lg\n    ";
        readonly button: {
            readonly base: "p-1.5 rounded transition-colors duration-150";
            readonly idle: "hover:bg-slate-700 text-slate-300 hover:text-white";
            readonly active: "bg-emerald-500/20 text-emerald-400";
            readonly speaking: "bg-amber-500/20 text-amber-400";
        };
        readonly icon: "w-3.5 h-3.5";
    };
    readonly dateDivider: {
        readonly container: "my-4 flex items-center gap-3";
        readonly line: "flex-1 h-px bg-gradient-to-r from-transparent via-slate-700/30 to-transparent";
        readonly label: "px-3 py-1 text-[10px] text-slate-500 font-medium bg-slate-900/50 rounded-full";
    };
    readonly typing: {
        readonly container: "flex items-center gap-2 px-4 py-2";
        readonly dot: "w-1.5 h-1.5 bg-amber-400/80 rounded-full";
        readonly animation: "animate-bounce";
    };
};
declare const markdownStyles: {
    readonly p: "mb-3 last:mb-0";
    readonly strong: "font-semibold text-white";
    readonly em: "italic text-slate-300";
    readonly code: "px-1 py-0.5 bg-slate-800/80 rounded text-amber-300/90 font-mono text-[13px]";
    readonly pre: "my-3 p-3 bg-slate-900/80 rounded-lg border border-slate-700/30 overflow-x-auto text-[13px]";
    readonly ul: "my-2 ml-0.5 space-y-1.5";
    readonly ol: "my-2 ml-0.5 space-y-1.5 list-decimal list-inside";
    readonly li: "flex gap-1.5 text-slate-200";
    readonly bullet: "text-slate-500 select-none text-[10px] mt-1";
    readonly h1: "text-lg font-semibold text-white mt-4 mb-2";
    readonly h2: "text-base font-semibold text-white mt-3 mb-1.5";
    readonly h3: "text-sm font-semibold text-slate-100 mt-2 mb-1";
    readonly blockquote: "my-3 px-4 py-3 rounded-lg bg-white/[0.03] border border-slate-700/40 border-l-2 border-l-amber-500/60 text-slate-200 text-[13.5px]";
    readonly link: "text-emerald-400 hover:text-emerald-300 underline underline-offset-2 transition-colors";
};

interface MessageContentProps {
    /** Is this a user message */
    isUser: boolean;
    /** Message content */
    content: string;
    /** Show streaming cursor */
    isStreaming?: boolean;
    /** Override how assistant content is rendered (default: markdown). */
    renderMarkdown?: (content: string) => ReactNode;
    /**
     * B3-FIGLASS-12 — clamp long content behind a "show more" disclosure
     * (ChatGPT parity for long pasted user messages). Never combine with
     * `isStreaming`: a live answer must stay fully visible while it grows.
     */
    collapsible?: boolean;
    /** Collapsed max height in px when `collapsible`. Default 264. */
    collapsedMaxHeight?: number;
    /** Disclosure copy (app-owned). Defaults: "Mostrar más" / "Mostrar menos". */
    showMoreLabel?: string;
    showLessLabel?: string;
    /** Class for the disclosure toggle button. */
    collapseToggleClassName?: string;
}
declare const MessageContent: react.NamedExoticComponent<MessageContentProps>;

/**
 * normalizeStreamedMarkdown — repair chunk-boundary glue in streamed LLM output
 * before markdown rendering (B3-FIGLASS-9).
 *
 * The staging audit showed an assistant reply rendering "…las herramientas
 * necesarias.## Respuesta sobre…" — the backend concatenated the pre-tool text
 * and the post-tool response without a newline, so the ATX heading never starts
 * a line and CommonMark (correctly) treats it as paragraph text.
 *
 * This is a NORMALIZER, not a parser: one conservative repair, applied only
 * outside fenced code blocks.
 *
 * Repair rule: a heading marker (`#{1,6} `) glued directly onto sentence-ending
 * punctuation gets a blank line inserted before it. Requiring the punctuation
 * (no whitespace in between) is what keeps false positives out:
 *  - `C# is nice`      → untouched (letter before `#`)
 *  - `issue #123`      → untouched (no space after `#`)
 *  - `use the # key`   → untouched (whitespace before `#`)
 *  - `fin.## Título`   → `fin.\n\n## Título` (the streaming-glue case)
 */
declare function normalizeStreamedMarkdown(content: string): string;

interface CopyButtonProps {
    /** Text to copy to the clipboard. */
    content: string;
    /** Called if the Clipboard API rejects (default: silent). */
    onError?: (error: unknown) => void;
    /** Override the button base class. */
    className?: string;
    /** Override the idle-state class. */
    idleClassName?: string;
    /** Override the copied-state class. */
    activeClassName?: string;
    /** Override the icon class. */
    iconClassName?: string;
    /** Tooltip/label before copy (default: "Copiar"). */
    copyLabel?: string;
    /** Tooltip/label after copy (default: "Copiado"). */
    copiedLabel?: string;
    /** Milliseconds before the check resets to copy (default: 2000). */
    resetMs?: number;
}
declare const CopyButton: react.NamedExoticComponent<CopyButtonProps>;

interface MessageBubbleProps {
    /** Drives alignment/background (user vs assistant). */
    role: 'user' | 'assistant';
    /** The message body (required). */
    children: ReactNode;
    /** Avatar + author/timestamp row. */
    header?: ReactNode;
    /** Reasoning / chain-of-thought block (rendered above the body). */
    reasoning?: ReactNode;
    /** Badge/chip rendered below the body (e.g. model, sources). */
    badge?: ReactNode;
    /** Hover action toolbar (e.g. copy, speak). */
    actions?: ReactNode;
    /** Extra classes appended to the article. */
    className?: string;
    /** Accessible label for the article. */
    ariaLabel?: string;
}
declare const MessageBubble: react.NamedExoticComponent<MessageBubbleProps>;

interface CollapsibleTextProps {
    children: ReactNode;
    /** Collapsed max height in px. Default 264 (11 lines at 24px leading). */
    maxHeight?: number;
    /** Height in px of the fade-out mask at the bottom of clamped content. Default 48. */
    fadeHeight?: number;
    /** Toggle copy when collapsed. Default: "Mostrar más". */
    showMoreLabel?: string;
    /** Toggle copy when expanded. Default: "Mostrar menos". */
    showLessLabel?: string;
    /** Wrapper class (style hook for the app). */
    className?: string;
    /** Toggle button class. When set, the unstyled default is dropped. */
    toggleClassName?: string;
}
declare function CollapsibleText({ children, maxHeight, fadeHeight, showMoreLabel, showLessLabel, className, toggleClassName, }: CollapsibleTextProps): react.JSX.Element;

interface MessageListGroup<T> {
    /** Stable key for the group (also passed to renderDivider). */
    key: string;
    /** Items belonging to this group. */
    items: T[];
}
interface MessageListProps<T> {
    /** Pre-grouped items (app decides the grouping strategy). */
    groups: MessageListGroup<T>[];
    /** Render a single item. Return value should carry its own React key. */
    renderItem: (item: T, index: number) => ReactNode;
    /** Optional per-group divider (e.g. a date separator). */
    renderDivider?: (key: string) => ReactNode;
    /** Class for the scroll/list container. */
    containerClassName?: string;
    /** Class for each group's inner item wrapper. */
    groupClassName?: string;
    /** Slot rendered before the groups. */
    header?: ReactNode;
    /** Slot rendered after the groups (streaming row, typing dots, spacer…). */
    footer?: ReactNode;
}
declare function MessageList<T>({ groups, renderItem, renderDivider, containerClassName, groupClassName, header, footer, }: MessageListProps<T>): react.JSX.Element;

export { CollapsibleText, type CollapsibleTextProps, CopyButton, type CopyButtonProps, MessageBubble, type MessageBubbleProps, MessageContent, type MessageContentProps, MessageList, type MessageListGroup, type MessageListProps, markdownStyles, messageStyles, normalizeStreamedMarkdown };
