import * as react from 'react';
import { ReactNode, CSSProperties, ChangeEvent, MouseEvent, KeyboardEvent } from 'react';
import { ToolCall, AgentTurnState, GuardRejection, AgentPlan, AgentTurnStatus, AgentHook, ChatMessage, VoiceAdapter } from '@free-intelligence/core';
import { LucideIcon } from 'lucide-react';

/**
 * Tool classification + live-status helpers for the Steps audit trail.
 *
 * Pure and generic — a raw tool name like `mcp__brightdata__scrape_as_markdown`
 * or `Bash` → a visual category + a short display name + a live status. No app
 * deps, no icons (the icon set maps a category → a component separately).
 */

type ToolCategory = 'search' | 'scrape' | 'browser' | 'rag' | 'bash' | 'introspect' | 'generic';
/** Classify a raw tool name into a visual category (loose substring match, so a
 * rename like `scrape_as_markdown` → `scrape_markdown` still resolves). */
declare function classifyTool(name: string): ToolCategory;
/** Strip the `mcp__<server>__` prefix for display (`scrape_as_markdown`). */
declare function shortToolName(name: string): string;
type ToolVisualStatus = 'active' | 'sent' | 'done' | 'error';
/** Index of the latest still-open (pending) tool — the one to highlight live. */
declare function latestOpenToolIndex(steps: ToolCall[]): number;
/** Visual status for one step: only the latest open step reads "active". */
declare function toolVisualStatus(step: ToolCall, index: number, latestOpenIndex: number, live: boolean): ToolVisualStatus;

/**
 * AgentIconSet — the icons the agent panels need, with lucide defaults.
 *
 * Icons are injectable per panel (the `icons` prop merges over these defaults),
 * so an app can swap the icon language without forking the components. The tool
 * map is keyed by visual category (see toolClassify), not lucide names, so a
 * swap is a one-line change here.
 */

interface AgentIconSet {
    /** Plan checklist header. */
    plan: LucideIcon;
    /** Guard/warning indicator. */
    warning: LucideIcon;
    /** In-progress spinner (e.g. the "still working" banner). Spun via animate-spin. */
    spinner: LucideIcon;
    /** Assistant identity (Steps panel header). */
    bot: LucideIcon;
    /** Sources panel header. */
    sources: LucideIcon;
    /** Outgoing-link arrow on each source row. */
    external: LucideIcon;
    /** Per-category tool icons for the Steps audit trail. */
    tools: Record<ToolCategory, LucideIcon>;
}
declare const defaultAgentIcons: AgentIconSet;
/** Merge caller overrides over the defaults (deep-merges the `tools` map). */
declare function resolveIcons(overrides?: Partial<AgentIconSet>): AgentIconSet;
/** Resolve the icon for a raw tool name via its category. */
declare function toolIcon(icons: AgentIconSet, name: string): LucideIcon;

/**
 * Class-name slots so the consuming app keeps its own CSS — fi-glass ships
 * neutral defaults (empty strings) and never hardcodes app-specific class names
 * (no `iai-*` / `aplay-*` leaking into the framework). insult_ai passes its
 * `iai-card-soft` / `iai-hint` / branded source-row strings to preserve render;
 * og118 passes its own (or nothing for the neutral look).
 */
interface AgentClassNames {
    /** Card/surface container of a panel. */
    card?: string;
    /** Dimmed small-text hint (counts, queued labels, guard tag). */
    hint?: string;
    /** A single source row (`<a>`) in the Sources panel. */
    sourceRow?: string;
}

interface AgentPanelProps {
    /**
     * The reduced state of one agentic turn (built by core's `applyAgentEvent`).
     * Passed directly — NOT via the AgentHook — because consumers render a panel
     * per historical turn/message, and the hook models only the current turn.
     * A single-turn app simply passes `agentHook.turn`.
     */
    turn: AgentTurnState;
    /** Optional target (URL/claim) for the Steps live label. */
    target?: string;
    classNames?: AgentClassNames;
    icons?: Partial<AgentIconSet>;
    enableSlowBanner?: boolean;
    slowThresholdMs?: number;
    /** Replace the default Sources panel (e.g. an app's branded source list). */
    renderSources?: (sources: string[]) => ReactNode;
    /** Override the guard-rejection banner (copy is app-owned). */
    renderGuardBanner?: (rejection: GuardRejection) => ReactNode;
}
/**
 * The glass-box agentic panel: Plan (contract, guard woven in) + Steps (live
 * audit trail) + Sources (evidence). Each sub-panel self-hides when it has
 * nothing to show, so an early/no-tool turn degrades gracefully.
 */
declare function AgentPanel({ turn, target, classNames, icons, enableSlowBanner, slowThresholdMs, renderSources, renderGuardBanner, }: AgentPanelProps): react.JSX.Element;

interface PlanChecklistProps {
    plan: AgentPlan | null;
    classNames?: AgentClassNames;
    icons?: Partial<AgentIconSet>;
    /**
     * Override the guard-rejection banner. The guard is a QUALITY woven into the
     * plan, not a separate widget — when a rejection is present this renders it.
     * The default copy is generic ("A guard blocked this plan"); apps that want
     * their own wording (e.g. "PlanGuard blocked this plan") pass this slot.
     */
    renderGuardBanner?: (rejection: GuardRejection) => ReactNode;
}
/**
 * The agent's plan-of-action as a live checklist. Renders only when a plan was
 * declared. Visual rule: signal > detail — this says WHAT the agent committed
 * to; the Steps panel shows every tool call as it happens.
 */
declare function PlanChecklist({ plan, classNames, icons, renderGuardBanner, }: PlanChecklistProps): react.JSX.Element | null;

interface StepsPanelProps {
    steps: ToolCall[];
    status: AgentTurnStatus;
    /** Optional target (URL/claim) the agent is working on, for the live label. */
    target?: string;
    classNames?: AgentClassNames;
    icons?: Partial<AgentIconSet>;
    /** Show the "still working" reassurance banner past the threshold (default true). */
    enableSlowBanner?: boolean;
    /** Milliseconds before the slow banner appears (default 12s). */
    slowThresholdMs?: number;
}
/**
 * Collapsible audit trail that lists every tool call as it happens. Auto-expands
 * while the turn is live and collapses on done. The "thinking" status is generic
 * here — fi-glass knows nothing about clinical/roast modes; the slow banner is a
 * plain prop (apps that have their own slow UI pass enableSlowBanner={false}).
 */
declare function StepsPanel({ steps, status, target, classNames, icons, enableSlowBanner, slowThresholdMs, }: StepsPanelProps): react.JSX.Element | null;

interface SourcesPanelProps {
    /** Evidence references (e.g. source URLs). Contract field name = `sources`. */
    sources: string[];
    classNames?: AgentClassNames;
    icons?: Partial<AgentIconSet>;
    /** Header label (default "Sources"). */
    label?: string;
}
/**
 * The Sources panel — the references the agent actually fetched/cited. fi-glass
 * ships a neutral default; an app with branded styling (e.g. insult_ai's Bright
 * Data receipts) can pass its row class via `classNames.sourceRow`, or replace
 * this whole panel through the AgentPanel's `renderSources` slot.
 */
declare function SourcesPanel({ sources, classNames, icons, label, }: SourcesPanelProps): react.JSX.Element | null;

/**
 * Predicate an app passes to CLAIM a specific error class as its own. When it
 * returns true for a failed turn, the conversation still reverts the optimistic
 * message but does NOT raise the generic recoverable `turnError` — the app shows
 * its own UI instead (e.g. og118's 401 token-gate banner, where a blind "retry"
 * would just 401 again). The idle-timeout failure is never app-handled.
 */
type AppHandledError = (turn: AgentTurnState) => boolean;
/** A recoverable failure of the in-flight turn, surfaced for retry/dismiss. */
interface TurnError {
    /** `timeout` = the idle watchdog fired; `stream` = the transport reported error. */
    kind: 'timeout' | 'stream';
    /** Human-readable, app-displayable reason. */
    message: string;
}
/** Default idle watchdog: a turn with no state change for this long is hung. */
declare const DEFAULT_TURN_TIMEOUT_MS = 60000;
interface UseAgentConversationOptions {
    /**
     * Controlled mode: when provided, the CONSUMER owns the visible thread. The
     * hook returns these verbatim as `conversation.messages` and stops folding —
     * `send` drives `agent.send(text)` but pushes no optimistic message and folds
     * no finished turn (the consumer maps its own transport into this transcript).
     * For workflow adapters whose single send yields many agent-handoff messages
     * (the 1-send -> 8+ messages case the single-turn fold cannot express; the
     * Activist OS canary that surfaced this). Mutually exclusive with
     * `initialMessages`/`conversationId`/`onMessagesChange` (those are bypassed —
     * the consumer owns persistence); if both `externalMessages` and
     * `initialMessages` are passed, `externalMessages` wins. Undefined =
     * uncontrolled (the hook owns the thread, byte-identical to before).
     */
    externalMessages?: ChatMessage[];
    /** Identity of the active conversation. When it changes, the thread re-hydrates. (Ignored in controlled mode.) */
    conversationId?: string | null;
    /** Messages to seed the thread with (the active conversation's stored transcript). (Ignored in controlled mode.) */
    initialMessages?: ChatMessage[];
    /** Called when the thread changes from real activity (fold/revert) — a persist hook. (Not called in controlled mode.) */
    onMessagesChange?: (messages: ChatMessage[]) => void;
    /**
     * Idle watchdog in ms: if the live turn's state does not change for this long
     * while streaming, the turn is declared failed (timeout). Measured since the
     * LAST turn-state change, not since send — a long-but-active turn (streaming
     * tokens, running steps) keeps resetting it and never trips. Pass a small
     * value in tests; `0` disables the watchdog. Defaults to 60s.
     */
    turnTimeoutMs?: number;
    /**
     * Claim a specific error class as app-handled (see {@link AppHandledError}).
     * Such a failure still reverts the optimistic message but is NOT surfaced as a
     * generic `turnError` — the app renders its own UI for it. Timeouts ignore this.
     */
    isAppHandledError?: AppHandledError;
}
interface AgentConversation {
    /** The visible thread of completed turns (user + assistant), in send order. */
    messages: ChatMessage[];
    /** The current/live turn's reduced state (for the in-flight glass-box). */
    turn: AgentTurnState;
    /**
     * Whether a turn is actively streaming. This is the CONVERSATION's view, not
     * the transport's: once the watchdog declares a turn hung, this is false even
     * if the underlying `agent.isStreaming` is still stuck true — so the surface
     * leaves the "thinking…" state and can render the recoverable error instead.
     */
    isStreaming: boolean;
    /** A recoverable failure of the last turn (timeout/stream), or null. */
    turnError: TurnError | null;
    /** Send a message: pushes it optimistically, then drives the agent turn. */
    send: (text: string) => void;
    /** Like send, but resolves with the assistant's final text (RESONANCE voice turns). */
    sendAndAwait: (text: string) => Promise<string>;
    /** Re-send the last user text after a failure. No-op if there is nothing to retry. */
    retry: () => void;
    /** Clear the current turnError without re-sending (the optimistic msg is already reverted). */
    dismissError: () => void;
    /** Clear the whole thread and reset the underlying turn/session. */
    newConversation: () => void;
}
declare function useAgentConversation(agent: AgentHook, options?: UseAgentConversationOptions): AgentConversation;

type AgentConversationSurfaceLayout = 'viewport' | 'contained';
interface AgentConversationSurfaceProps {
    /** The conversation state + actions from `useAgentConversation`. */
    conversation: AgentConversation;
    /**
     * FG-2 (canary-driven, activist-os): how the surface root sizes itself.
     *  - `"viewport"` (DEFAULT): root is `height: 100dvh` — the full-page behavior
     *    every existing consumer relies on.
     *  - `"contained"`: root is `height: 100%` + `minHeight: 0` + `overflow: hidden`,
     *    so it fills whatever fixed-height cell an app shell gives it (header + main
     *    + artifacts rail + footer) and scrolls the transcript internally instead of
     *    forcing page scroll.
     */
    layout?: AgentConversationSurfaceLayout;
    /** Composer placeholder copy (app-owned). */
    composerPlaceholder?: string;
    /** Label for the new-conversation button. Default: "New chat". */
    newChatLabel?: string;
    /**
     * Render the built-in new-conversation button above the composer. Default
     * true. An app whose chrome already owns that affordance (e.g. a sidebar's
     * "+ New chat") sets false to avoid a duplicate CTA (B3-OG118-5) — a typed
     * opt-out, not consumer CSS hiding framework internals.
     */
    showNewChatButton?: boolean;
    /** Rendered when the thread is empty and idle (e.g. an app start screen). */
    emptyState?: ReactNode;
    /** Slot rendered just above the composer (e.g. an app's auth banner). */
    aboveComposer?: ReactNode;
    /** Pass-through styling/icons for the live-turn AgentPanel. */
    agentPanelProps?: Partial<Omit<AgentPanelProps, 'turn'>>;
    /**
     * B3-FIGLASS-TRACE-PERSISTENCE-1 — re-render the persisted glass-box trace
     * (declared plan + steps + tool calls + sources) above each assistant message
     * that carries one, using the SAME AgentPanel as the live turn. This makes the
     * differentiator — "see the execution, not just the result" — survive into the
     * durable transcript instead of collapsing to the answer text on fold. Default
     * true; a surface that wants answer-only history sets false. Messages with no
     * `trace` (plain conversational turns, user messages) render unchanged.
     */
    showPersistedTrace?: boolean;
    /**
     * Floating composer box class (style hook for the app) — the single frosted
     * container that wraps BOTH the textarea row and the controls row (mic/send),
     * mirroring the shell's `chat-input-floating-box` (AURITY). Apply the
     * glass-chat preset here (`glass-chat-composer`), not on `composerAreaClassName`:
     * the controls belong INSIDE the box, not floating next to it.
     */
    composerBoxClassName?: string;
    /** Composer textarea-row wrapper class (spacing inside the box). */
    composerAreaClassName?: string;
    /** Composer textarea class (style hook for the app). */
    composerTextareaClassName?: string;
    /** Controls-row class (the mic/send row inside the box; layout stays framework-owned). */
    composerControlsClassName?: string;
    /**
     * When true (and no `renderActions` override), each transcript message gets a
     * default {@link CopyButton} in the bubble's actions slot. Default: false
     * (the dense agentic surface stays action-free unless the app opts in). The
     * live streaming message never gets a copy action.
     */
    showCopyAction?: boolean;
    /** Per-message header slot (avatar + author/meta) → MessageBubble.header. */
    renderHeader?: (message: ChatMessage) => ReactNode;
    /** Per-message badge slot (model/provenance chip) → MessageBubble.badge. */
    renderBadge?: (message: ChatMessage) => ReactNode;
    /** Per-message actions slot (overrides showCopyAction) → MessageBubble.actions. */
    renderActions?: (message: ChatMessage) => ReactNode;
    /**
     * Extra class for message bubbles → MessageBubble.className.
     *
     * Accepts either:
     *  - a `string` applied to EVERY bubble regardless of role (legacy, unchanged), or
     *  - a `(message) => string | undefined` resolver so a consumer can return a
     *    DIFFERENT class per role (e.g. `glass-chat-bubble-user` vs
     *    `glass-chat-bubble-assistant`) without re-implementing the surface or
     *    duplicating MessageBubble.
     *
     * B3-VOICE-FIGLASS-3: the tri-consumer visual audit found the only real
     * reusable gap was that this surface could not vary bubble styling by role —
     * og118 was forced to apply one assistant class to user AND assistant. The
     * function form closes that gap. Backward-compatible: omit it for defaults,
     * pass a string for the previous all-roles behavior. The resolver is also
     * called for the live streaming (assistant) bubble; a resolver that returns
     * `undefined` for any message (e.g. an unknown role) simply yields no extra
     * class, so it never throws.
     */
    messageBubbleClassName?: string | ((message: ChatMessage) => string | undefined);
    /**
     * The app's voice engine. When it exposes `transcribe`, the surface lights up
     * an in-composer dictation mic and feeds the recognized text straight into the
     * composer — no consumer wiring, exactly how a `synthesize`-capable adapter
     * lights up the SpeakButton. Omit it (or pass one without `transcribe`) and
     * there is no mic at all (backward-compatible default).
     *
     * B3-VOICE-FIGLASS-4: the STT canary (og118) revealed the surface owned the
     * composer's text state with no way to receive dictated text. Rather than
     * thread a callback, the surface consumes the VoiceAdapter capability — the
     * pattern core prescribes ("add a capability via an adapter member, never by
     * threading a new callback through the components").
     */
    voiceAdapter?: VoiceAdapter;
    /** Class for the dictation mic slot wrapper (only rendered when STT is available). */
    micSlotClassName?: string;
    /** Class for the dictation mic button. */
    micButtonClassName?: string;
    /** Called on a recording/transcription failure surfaced by dictation. */
    onVoiceError?: (message: string) => void;
    /**
     * Wrapper class for the live dictation visualizer (the equalizer that reacts
     * to the mic while recording). Only rendered while dictation is active, fed by
     * the analyser's frequency bands — so every shell inherits reactive bars
     * without re-wiring Web Audio. Omit for the unstyled default.
     */
    voiceVisualizerClassName?: string;
    /** Per-bar class for the live dictation visualizer. */
    voiceVisualizerBarClassName?: string;
    /**
     * Render an explicit send button in the composer row (in addition to
     * Enter-to-send). Default true — a visible affordance matches the shell
     * composer (AURITY). Set false for an Enter-only composer.
     */
    showSendButton?: boolean;
    /** Class for the send button. */
    sendButtonClassName?: string;
    /** Class for the send button icon. */
    sendButtonIconClassName?: string;
    /** aria-label for the send button. Default: "Enviar mensaje". */
    sendLabel?: string;
    /**
     * B3-VOICE-OG118-6 — append text to the composer from an external source
     * (e.g. a durable-queue transcription). When non-empty, the surface appends
     * this text to the current input and calls `onComposerAppendConsumed`. Pull-once
     * pattern: set to a string → surface consumes → consumer resets to ''.
     */
    composerAppend?: string;
    /** Called immediately after the surface appends `composerAppend`. Reset to ''. */
    onComposerAppendConsumed?: () => void;
    /**
     * B3-VOICE-OG118-6 — replace the built-in `ComposerMicSlot` + `useDictation`
     * with custom content (e.g. a durable-recording button). When provided, no
     * built-in mic is rendered and no dictation visualizer is shown. The `voiceAdapter`
     * prop still gates TTS-only features; pass `undefined` or an adapter without
     * `transcribe` to avoid a phantom built-in mic alongside the override.
     */
    micSlotOverride?: ReactNode;
    /**
     * B3-FIGLASS-8 — recoverable turn-failure UI. When `conversation.turnError`
     * is set (a hung/timed-out or errored turn), the surface renders a recoverable
     * banner with retry/dismiss INSTEAD of the zombie "thinking…" panel. These are
     * the consumer's style/copy hooks; sensible defaults render without any.
     */
    errorClassName?: string;
    /** Retry button copy. Default: "Reintentar". */
    retryLabel?: string;
    /** Dismiss button copy. Default: "Descartar". */
    dismissLabel?: string;
    /** Class for the retry button. */
    retryButtonClassName?: string;
    /** Class for the dismiss button. */
    dismissButtonClassName?: string;
    /**
     * B3-FIGLASS-12 — pin-to-bottom scroll during streaming (ChatGPT parity).
     * The transcript stays pinned to the newest content while a turn streams;
     * the user scrolling up unpins it; a floating button jumps back. Powered by
     * use-stick-to-bottom (ResizeObserver + spring, no overflow-anchor — Safari
     * doesn't support it). Default true. This finally consumes the autoscroll
     * promise that config.ts declared and nothing implemented.
     */
    autoScroll?: boolean;
    /** aria-label for the floating scroll-to-bottom button. Default: "Ir al final". */
    scrollToBottomLabel?: string;
    /** Visual class for the scroll-to-bottom button (placement stays framework-owned). */
    scrollToBottomClassName?: string;
    /** Icon class for the scroll-to-bottom button. */
    scrollToBottomIconClassName?: string;
    /**
     * B3-FIGLASS-12 — clamp long USER messages behind a "show more" disclosure
     * (ChatGPT parity: max-height + mask-image fade + aria-expanded toggle).
     * Assistant messages and the live streaming bubble are never clamped.
     * Default true.
     */
    collapseUserMessages?: boolean;
    /** Collapsed max height in px. Default 264 (11 lines at 24px leading). */
    collapseMaxHeight?: number;
    /** Disclosure copy (app-owned). Defaults: "Mostrar más" / "Mostrar menos". */
    showMoreLabel?: string;
    showLessLabel?: string;
    /** Class for the disclosure toggle button. */
    collapseToggleClassName?: string;
}
declare function AgentConversationSurface({ conversation, layout, composerPlaceholder, newChatLabel, showNewChatButton, emptyState, aboveComposer, agentPanelProps, showPersistedTrace, composerBoxClassName, composerAreaClassName, composerTextareaClassName, composerControlsClassName, showCopyAction, renderHeader, renderBadge, renderActions, messageBubbleClassName, voiceAdapter, micSlotClassName, micButtonClassName, onVoiceError, voiceVisualizerClassName, voiceVisualizerBarClassName, showSendButton, sendButtonClassName, sendButtonIconClassName, sendLabel, composerAppend, onComposerAppendConsumed, micSlotOverride, errorClassName, retryLabel, dismissLabel, retryButtonClassName, dismissButtonClassName, autoScroll, scrollToBottomLabel, scrollToBottomClassName, scrollToBottomIconClassName, collapseUserMessages, collapseMaxHeight, showMoreLabel, showLessLabel, collapseToggleClassName, }: AgentConversationSurfaceProps): react.JSX.Element;

interface ScrollToBottomButtonProps {
    onClick: () => void;
    /** Accessible label. Default: "Ir al final". */
    label?: string;
    /** Visual class. When set, the default skin is dropped (placement stays). */
    className?: string;
    /** Icon class. */
    iconClassName?: string;
}
declare function ScrollToBottomButton({ onClick, label, className, iconClassName, }: ScrollToBottomButtonProps): react.JSX.Element;

type AgentWorkspaceShellVisual = 'aurora' | 'midnight' | 'clinical';
type AgentWorkspaceShellDensity = 'compact' | 'comfortable' | 'spacious';
/** Imperative drawer controls handed to the sidebar slot in `responsive` mode. */
interface AgentWorkspaceShellApi {
    /** Whether the mobile drawer is open (always false on desktop / non-responsive). */
    isOpen: boolean;
    /** Whether the shell is in the mobile/drawer breakpoint. */
    isMobile: boolean;
    open: () => void;
    close: () => void;
    toggle: () => void;
}
type SidebarSlot = ReactNode | ((api: AgentWorkspaceShellApi) => ReactNode);
interface AgentWorkspaceShellProps {
    visual?: AgentWorkspaceShellVisual;
    density?: AgentWorkspaceShellDensity;
    header?: ReactNode;
    conversation: ReactNode;
    rail?: ReactNode;
    footer?: ReactNode;
    /**
     * Optional left chrome (e.g. a conversation list). A render function receives
     * the drawer api so the consumer can `close()` on selection/new without the
     * shell touching its internals. Omit it for the original page primitive.
     */
    sidebar?: SidebarSlot;
    /**
     * Opt into the mobile drawer behavior for the `sidebar`. Default `false` keeps
     * the sidebar a static column at every width. No effect without `sidebar`.
     */
    responsive?: boolean;
    /** Media query that switches the sidebar into drawer mode. Default `(max-width: 768px)`. */
    mobileQuery?: string;
    /** Desktop sidebar width (number → px). Default `280`. */
    sidebarWidth?: number | string;
    /** Accessible label for the drawer toggle. Default `Conversaciones`. */
    toggleLabel?: string;
    className?: string;
    style?: CSSProperties;
}
declare function AgentWorkspaceShell({ visual, density, header, conversation, rail, footer, sidebar, responsive, mobileQuery, sidebarWidth, toggleLabel, className, style, }: AgentWorkspaceShellProps): react.JSX.Element;

interface ItemActionSlotProps {
    /** Accessible label — the consumer supplies the copy (e.g. "Renombrar chat"). */
    label: string;
    /** Fired on click/activation; the click never bubbles to the row's onSelect. */
    onActivate: () => void;
    disabled?: boolean;
    /** Tint the action as destructive (danger color on hover). */
    danger?: boolean;
    className?: string;
    /** The glyph/icon to render inside the button. */
    children: ReactNode;
}
declare function ItemActionSlot({ label, onActivate, disabled, danger, className, children, }: ItemActionSlotProps): react.JSX.Element;
type DestructiveActionSlotProps = Omit<ItemActionSlotProps, 'danger'>;
declare function DestructiveActionSlot(props: DestructiveActionSlotProps): react.JSX.Element;
interface UseInlineRenameOptions {
    maxLength?: number;
    /**
     * What an empty draft means on commit. `revert` (default) calls `onRename('')`
     * so the consumer can fall back to an auto-derived title; `keep` cancels
     * silently and leaves the current value.
     */
    emptyPolicy?: 'revert' | 'keep';
}
interface InlineRename {
    editing: boolean;
    draft: string;
    start: () => void;
    cancel: () => void;
    /** Spread onto the `<input>` — wires value, Enter/Escape/blur, and click-stop. */
    inputProps: {
        value: string;
        maxLength?: number;
        autoFocus: true;
        onChange: (e: ChangeEvent<HTMLInputElement>) => void;
        onBlur: () => void;
        onClick: (e: MouseEvent) => void;
        onKeyDown: (e: KeyboardEvent) => void;
    };
}
declare function useInlineRename(value: string, onRename: (next: string) => void, { maxLength, emptyPolicy }?: UseInlineRenameOptions): InlineRename;
interface AgentSidebarItemProps {
    selected: boolean;
    onSelect: () => void;
    /** A plain string is wrapped in the title slot; a node (e.g. the rename input) is used as-is. */
    title: ReactNode;
    subtitle?: ReactNode;
    meta?: ReactNode;
    /** Action buttons rendered at the end of the row (e.g. {@link DestructiveActionSlot}). */
    actions?: ReactNode;
    disabled?: boolean;
    /** When the row is being edited in place: non-interactive, no hover-select. */
    editing?: boolean;
    ariaLabel?: string;
    className?: string;
}
declare function AgentSidebarItem({ selected, onSelect, title, subtitle, meta, actions, disabled, editing, ariaLabel, className, }: AgentSidebarItemProps): react.JSX.Element;
interface EditableResourceItemProps {
    title: string;
    selected: boolean;
    onSelect: () => void;
    onRename: (next: string) => void;
    subtitle?: ReactNode;
    meta?: ReactNode;
    /** Extra actions (e.g. delete) rendered after the rename trigger. */
    actions?: ReactNode;
    disabled?: boolean;
    maxLength?: number;
    emptyPolicy?: 'revert' | 'keep';
    /** Accessible label for the rename trigger (consumer copy). */
    renameLabel: string;
    /** Accessible label for the rename input (consumer copy). */
    renameInputLabel: string;
    /** Glyph for the rename trigger; defaults to a pencil. */
    renameGlyph?: ReactNode;
    ariaLabel?: string;
}
declare function EditableResourceItem({ title, selected, onSelect, onRename, subtitle, meta, actions, disabled, maxLength, emptyPolicy, renameLabel, renameInputLabel, renameGlyph, ariaLabel, }: EditableResourceItemProps): react.JSX.Element;

declare const FI_SIDEBAR_ITEM_CLASS = "fi-sidebar-item";
declare const FI_ITEM_TITLE_CLASS = "fi-sidebar-item-title";
declare const FI_ITEM_SUBTITLE_CLASS = "fi-sidebar-item-subtitle";
declare const FI_ITEM_META_CLASS = "fi-sidebar-item-meta";
declare const FI_ITEM_ACTION_CLASS = "fi-item-action";
declare const FI_RESOURCE_RENAME_INPUT_CLASS = "fi-resource-rename-input";
/** Inject the idempotent sidebar-item stylesheet (no-op on the server / if already present). */
declare function ensureSidebarItemStyle(): void;
/** Ensure the sidebar-item stylesheet is present for the lifetime of the component. */
declare function useSidebarItemStyle(): void;

interface AgentSidebarSectionProps {
    /** A plain string is wrapped in the title slot; a node (e.g. branded markup) is used as-is. */
    title: ReactNode;
    /** The rows (e.g. a `<nav>` of {@link AgentSidebarItem}). Shown when `count > 0`. */
    children: ReactNode;
    /** Header action affordance rendered at the end of the head row (e.g. a "+ Nuevo" button). */
    actionSlot?: ReactNode;
    /** Shown instead of `children` when `count === 0`. Omit to always render `children`. */
    emptyState?: ReactNode;
    /** Number of rows; gates whether `emptyState` (0) or `children` (>0) renders. */
    count: number;
    /** Replaces the default head (title + actionSlot) entirely when the consumer needs a custom header. */
    headerSlot?: ReactNode;
    /**
     * Distribution variant. `"plain"` (default) is the original borderless section —
     * unchanged for existing consumers. `"card"` wraps the section in a padded,
     * bordered, rounded card (token-driven via `--fi-section-card-*` + `--fi-radius-section`)
     * so a sidebar group reads as a distinct surface with breathing room.
     */
    variant?: 'plain' | 'card';
    /**
     * Content rendered BELOW the rows/empty-state, separated by a divider + gap (e.g.
     * an upload dropzone that must not collide with the list). Omit for no footer.
     */
    footerSlot?: ReactNode;
    /**
     * How the rows region sizes. `"none"` (default) lets the rows take their natural
     * height (the original behavior). `"content"` wraps the rows in a content-aware
     * scroll region: they grow by content and only scroll past `maxBlockSize` — a
     * rem-based cap, NOT a viewport `vh` that crushes a few rows on short screens.
     */
    scrollBehavior?: 'none' | 'content';
    /**
     * The scroll cap for `scrollBehavior="content"` (number → px). Default `18rem`
     * (~6 rows). Sets the `--fi-section-scroll-max` token on the scroll region.
     */
    maxBlockSize?: number | string;
    /** Accessible label for the section element. */
    ariaLabel?: string;
    className?: string;
}
declare function AgentSidebarSection({ title, children, actionSlot, emptyState, count, headerSlot, variant, footerSlot, scrollBehavior, maxBlockSize, ariaLabel, className, }: AgentSidebarSectionProps): react.JSX.Element;

declare const FI_SIDEBAR_SECTION_CLASS = "fi-sidebar-section";
declare const FI_SECTION_HEAD_CLASS = "fi-sidebar-section-head";
declare const FI_SECTION_TITLE_CLASS = "fi-sidebar-section-title";
declare const FI_SECTION_CARD_CLASS = "fi-sidebar-section--card";
declare const FI_SECTION_FOOTER_CLASS = "fi-sidebar-section-footer";
declare const FI_SECTION_SCROLL_CLASS = "fi-sidebar-section-scroll";
/** Inject the idempotent sidebar-section stylesheet (no-op on the server / if already present). */
declare function ensureSidebarSectionStyle(): void;
/** Ensure the sidebar-section stylesheet is present for the lifetime of the component. */
declare function useSidebarSectionStyle(): void;

/** Inject the idempotent density/spacing stylesheet (no-op on the server / if already present). */
declare function ensureDensityStyle(): void;
/** Ensure the density/spacing stylesheet is present for the lifetime of the component. */
declare function useDensityStyle(): void;

export { type AgentClassNames, type AgentConversation, AgentConversationSurface, type AgentConversationSurfaceLayout, type AgentConversationSurfaceProps, type AgentIconSet, AgentPanel, type AgentPanelProps, AgentSidebarItem, type AgentSidebarItemProps, AgentSidebarSection, type AgentSidebarSectionProps, AgentWorkspaceShell, type AgentWorkspaceShellApi, type AgentWorkspaceShellDensity, type AgentWorkspaceShellProps, type AgentWorkspaceShellVisual, type AppHandledError, DEFAULT_TURN_TIMEOUT_MS, DestructiveActionSlot, type DestructiveActionSlotProps, EditableResourceItem, type EditableResourceItemProps, FI_ITEM_ACTION_CLASS, FI_ITEM_META_CLASS, FI_ITEM_SUBTITLE_CLASS, FI_ITEM_TITLE_CLASS, FI_RESOURCE_RENAME_INPUT_CLASS, FI_SECTION_CARD_CLASS, FI_SECTION_FOOTER_CLASS, FI_SECTION_HEAD_CLASS, FI_SECTION_SCROLL_CLASS, FI_SECTION_TITLE_CLASS, FI_SIDEBAR_ITEM_CLASS, FI_SIDEBAR_SECTION_CLASS, type InlineRename, ItemActionSlot, type ItemActionSlotProps, PlanChecklist, type PlanChecklistProps, ScrollToBottomButton, type ScrollToBottomButtonProps, SourcesPanel, type SourcesPanelProps, StepsPanel, type StepsPanelProps, type ToolCategory, type ToolVisualStatus, type TurnError, type UseAgentConversationOptions, type UseInlineRenameOptions, classifyTool, defaultAgentIcons, ensureDensityStyle, ensureSidebarItemStyle, ensureSidebarSectionStyle, latestOpenToolIndex, resolveIcons, shortToolName, toolIcon, toolVisualStatus, useAgentConversation, useDensityStyle, useInlineRename, useSidebarItemStyle, useSidebarSectionStyle };
