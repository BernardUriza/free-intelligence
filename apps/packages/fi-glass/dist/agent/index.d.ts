import * as react from 'react';
import { ReactNode, CSSProperties, ChangeEvent, MouseEvent, KeyboardEvent } from 'react';
import { ToolCall, AgentTurnState, GuardRejection, AgentPlan, AgentTurnStatus, AgentHook, MessageAuthor, ChatMessage, MessageImage, VoiceAdapter } from '@free-intelligence/core';
import { LucideIcon } from 'lucide-react';
import { b as ComposerAction } from '../ComposerActions-HOiu1DmD.js';

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
/**
 * A failure to SAVE the thread (the turn itself succeeded). Distinct from
 * {@link TurnError}: the answer is on screen and correct — what failed is the
 * write, so the message the user must see is "this is not saved", not "the
 * answer failed".
 */
interface PersistError {
    /** Human-readable, app-displayable reason. */
    message: string;
    /** The underlying rejection, for the app to log/inspect. */
    cause: unknown;
}
/** Default idle watchdog: a turn with no state change for this long is hung. */
declare const DEFAULT_TURN_TIMEOUT_MS = 60000;
interface UseAgentConversationOptions {
    /**
     * WHO the agent is — REQUIRED. Every message this hook folds is stamped with an
     * author: the turn's own speaker when the backend announced one (the `author`
     * event — a selected persona/element), this identity otherwise. There is no
     * anonymous fold, because a transcript that cannot say who spoke silently
     * attributes every answer to the app (og118 labelled Yodo's answers "og118" for
     * exactly as long as this was optional).
     */
    author: MessageAuthor;
    /** WHO the human is. Defaults to {@link DEFAULT_USER_AUTHOR}. */
    userAuthor?: MessageAuthor;
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
    /**
     * Called when the thread changes from real activity (fold/revert) — a persist
     * hook. (Not called in controlled mode.)
     *
     * MAY be async: the hook awaits what it returns and surfaces a rejection as
     * {@link AgentConversation.persistError}. It used to be typed `=> void` while
     * consumers passed an async persist, so the promise was DISCARDED and a failed
     * save (a 413 for an oversized record, a dead network, a 500) died as an
     * unhandled rejection — the user saw the thread on screen, believed it was
     * saved, and lost it on reload. Silence is the one thing persistence may never do.
     */
    onMessagesChange?: (messages: ChatMessage[]) => void | Promise<void>;
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
     * The agent's own identity — who the live turn is attributed to until the
     * backend names a different speaker (`turn.author`). The surface reads it from
     * here, so the consumer declares the author once, at the hook.
     */
    author: MessageAuthor;
    /**
     * Whether a turn is actively streaming. This is the CONVERSATION's view, not
     * the transport's: once the watchdog declares a turn hung, this is false even
     * if the underlying `agent.isStreaming` is still stuck true — so the surface
     * leaves the "thinking…" state and can render the recoverable error instead.
     */
    isStreaming: boolean;
    /** A recoverable failure of the last turn (timeout/stream), or null. */
    turnError: TurnError | null;
    /**
     * The thread could not be SAVED (the turn itself succeeded), or null. A shell
     * MUST surface this: the alternative is a user who trusts a thread that is not
     * there. Recover with {@link retryPersist}.
     */
    persistError: PersistError | null;
    /** Retry saving the current thread. No-op when there is nothing pending. */
    retryPersist: () => void;
    /** Clear the persist error without retrying (the thread stays unsaved). */
    dismissPersistError: () => void;
    /**
     * The text of a turn that FAILED, reverted out of the thread — the shell puts
     * it back in the composer so the user does not lose what they wrote. Null when
     * nothing is pending recovery.
     */
    unsentText: string | null;
    /** Called by the shell once it has restored `unsentText` into the composer. */
    clearUnsentText: () => void;
    /** Send a message: pushes it optimistically, then drives the agent turn.
     * `images` attaches vision input (OG118-IMAGE-UPLOAD-1); an image-only send
     * (empty text, ≥1 image) is valid — the picture IS the message. */
    send: (text: string, images?: MessageImage[]) => void;
    /** Like send, but resolves with the assistant's final text (RESONANCE voice turns). */
    sendAndAwait: (text: string) => Promise<string>;
    /**
     * Cancel the streaming turn at the user's request. Present only when the
     * transport supports {@link AgentHook.abort} — a surface renders its stop
     * affordance off this being defined, never off `isStreaming` alone.
     *
     * A user stop is NOT a failure: the partial text the assistant already wrote
     * is folded into the thread (ChatGPT parity) and the optimistic user message
     * stays. That behavior is not re-implemented here — aborting drops
     * `isStreaming` without an error event, so the existing fold effect settles
     * the turn on its own.
     */
    stop?: () => void;
    /** Re-send the last user text after a failure. No-op if there is nothing to retry. */
    retry: () => void;
    /** Clear the current turnError without re-sending (the optimistic msg is already reverted). */
    dismissError: () => void;
    /** Clear the whole thread and reset the underlying turn/session. */
    newConversation: () => void;
}
declare function useAgentConversation(agent: AgentHook, options: UseAgentConversationOptions): AgentConversation;

/**
 * fi-glass · conversation-surface/types — the public contract of
 * AgentConversationSurface. The props are the surface's documented API (every
 * slot/copy/style hook a consumer can inject).
 *
 * DECOMPOSITION (B3-FIGLASS-SURFACE-PROPS-1): the contract used to be one
 * 56-field interface — a god-props object where every new capability grew the
 * same monolith and the regions had to receive the whole thing because
 * re-threading 56 props was unviable. It is now split into cohesive, individually
 * documented sub-interfaces (layout, slots, composer, send controls, message
 * rendering, dictation, image attachments, turn-error, autoscroll, collapse).
 * `AgentConversationSurfaceProps` composes them via `extends`, so the flat prop
 * surface consumers pass is UNCHANGED — this is a pure type-architecture refactor,
 * not a call-site break. New capabilities now land in the relevant slice instead
 * of the monolith, and each slice is a reusable, exported unit a region can type
 * against.
 *
 * Re-exported from `../AgentConversationSurface` — consumers never import from
 * this path.
 */

type AgentConversationSurfaceLayout = 'viewport' | 'contained';
/** Root sizing behavior of the surface. */
interface SurfaceLayoutProps {
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
}
/** App-owned content slots that stack around the transcript/composer. */
interface SurfaceSlotProps {
    /** Rendered when the thread is empty and idle (e.g. an app start screen). */
    emptyState?: ReactNode;
    /** Slot rendered just above the composer (e.g. an app's auth banner). */
    aboveComposer?: ReactNode;
}
/** The built-in new-conversation CTA above the composer. */
interface NewConversationProps {
    /** Label for the new-conversation button. Default: "New chat". */
    newChatLabel?: string;
    /**
     * Render the built-in new-conversation button above the composer. Default
     * true. An app whose chrome already owns that affordance (e.g. a sidebar's
     * "+ New chat") sets false to avoid a duplicate CTA (B3-OG118-5) — a typed
     * opt-out, not consumer CSS hiding framework internals.
     */
    showNewChatButton?: boolean;
}
/**
 * ComposerFrame slots, style hooks, the "+" action menu, and the external
 * append channel — everything about the box the user composes IN, minus the
 * send/stop controls (see SendControlProps) and dictation (see DictationProps).
 */
interface ComposerFrameProps {
    /** Composer placeholder copy (app-owned). */
    composerPlaceholder?: string;
    /**
     * Header slot INSIDE the composer box (ComposerFrame's header) — drafts and
     * previews that belong to the message being composed, e.g. a recorded-audio
     * draft (COMPOSER-FRAME-2). Renders between the box edge and the textarea;
     * the wrapper exists only while the slot is filled. Contrast with
     * `aboveComposer`, which stacks OUTSIDE the box (system banners, queues).
     */
    composerHeader?: ReactNode;
    /** Class for the composer header slot wrapper (e.g. a consumer's divider row). */
    composerHeaderClassName?: string;
    /**
     * Footer LEFT-rail slot INSIDE the composer box (ComposerFrame's footerStart)
     * — the tool-chip zone: model/persona selector, attach, a voice-call control.
     * Anything the user sets BEFORE composing, and that would otherwise grow into
     * its own card above the box (B3-FIGLASS-COMPOSER-FOOTER-ZONES-1).
     *
     * Contrast with `aboveComposer` (system banners that must interrupt) and
     * `composerHeader` (previews OF the message being composed).
     */
    composerFooterStart?: ReactNode;
    /** Class for the footer left-rail wrapper. */
    composerFooterStartClassName?: string;
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
     * Extra actions for the composer's "+" menu — anything the app lets the user
     * ADD to a turn (upload a document to the active project, …). Attaching an
     * image is contributed by the framework when `images` is wired; these are
     * appended after it, in one menu, so a new capability never grows the rail.
     */
    composerActions?: ComposerAction[];
    /** aria-label/title of the "+" trigger. Default: "Añadir". */
    composerActionsLabel?: string;
    composerActionsMenuClassName?: string;
    composerActionsItemClassName?: string;
    /**
     * B3-VOICE-OG118-6 — append text to the composer from an external source
     * (e.g. a durable-queue transcription). When non-empty, the surface appends
     * this text to the current input and calls `onComposerAppendConsumed`. Pull-once
     * pattern: set to a string → surface consumes → consumer resets to ''.
     */
    composerAppend?: string;
    /** Called immediately after the surface appends `composerAppend`. Reset to ''. */
    onComposerAppendConsumed?: () => void;
}
/** The send/stop button in the composer controls row. */
interface SendControlProps {
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
     * Class applied to the send button ADDITIVELY while it is a stop button
     * (streaming + the transport can abort) — e.g. a consumer's danger tint.
     */
    stopButtonClassName?: string;
    /** aria-label for the stop button. Default: "Detener respuesta". */
    stopLabel?: string;
}
/** Per-message rendering: glass-box trace, copy action, and bubble slot hooks. */
interface MessageRenderProps {
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
     * When true (and no `renderActions` override), each transcript message gets a
     * default CopyButton in the bubble's actions slot. Default: false
     * (the dense agentic surface stays action-free unless the app opts in). The
     * live streaming message never gets a copy action.
     */
    showCopyAction?: boolean;
    /** Copy for the "retry saving" button on the persist-failure banner. */
    persistRetryLabel?: string;
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
}
/** In-composer dictation (STT) via the app's VoiceAdapter, plus the mic slot. */
interface DictationProps {
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
     * B3-VOICE-OG118-6 — replace the built-in `ComposerMicSlot` + `useDictation`
     * with custom content (e.g. a durable-recording button). When provided, no
     * built-in mic is rendered and no dictation visualizer is shown. The `voiceAdapter`
     * prop still gates TTS-only features; pass `undefined` or an adapter without
     * `transcribe` to avoid a phantom built-in mic alongside the override.
     */
    micSlotOverride?: ReactNode;
}
/** Image attachments in the composer (ChatGPT parity). */
interface ImageAttachmentProps {
    /**
     * OG118-IMAGE-UPLOAD-1 — image attachments in the composer (ChatGPT parity).
     * When true, the surface owns the whole capability: an attach button in the
     * composer's footer rail (before `composerFooterStart`), paste-an-image into
     * the textarea, thumbnail chips in the composer header, downscale + base64
     * encoding, and sending the images with the message (`conversation.send`'s
     * second argument). Default false — no consumer wiring beyond this switch.
     */
    imageAttachments?: boolean;
    /** Max images attachable to one message. Default 4 (mirrors the server cap). */
    maxAttachedImages?: number;
    /** aria-label for the attach button. Default: "Adjuntar imagen". */
    attachImageLabel?: string;
    /** Class for the attach button. */
    attachImageButtonClassName?: string;
    /** Class for the attached-image chips row (composer header). */
    imageChipsClassName?: string;
    /** Called with a human-readable message when an image is rejected (type/size). */
    onImageAttachmentError?: (message: string) => void;
}
/**
 * B3-FIGLASS-8 — recoverable turn-failure UI. When `conversation.turnError`
 * is set (a hung/timed-out or errored turn), the surface renders a recoverable
 * banner with retry/dismiss INSTEAD of the zombie "thinking…" panel. These are
 * the consumer's style/copy hooks; sensible defaults render without any.
 */
interface TurnErrorProps {
    errorClassName?: string;
    /** Retry button copy. Default: "Reintentar". */
    retryLabel?: string;
    /** Dismiss button copy. Default: "Descartar". */
    dismissLabel?: string;
    /** Class for the retry button. */
    retryButtonClassName?: string;
    /** Class for the dismiss button. */
    dismissButtonClassName?: string;
}
/**
 * B3-FIGLASS-12 — pin-to-bottom scroll during streaming (ChatGPT parity).
 * The transcript stays pinned to the newest content while a turn streams;
 * the user scrolling up unpins it; a floating button jumps back. Powered by
 * use-stick-to-bottom (ResizeObserver + spring, no overflow-anchor — Safari
 * doesn't support it).
 */
interface AutoScrollProps {
    /** Default true. This finally consumes the autoscroll promise that config.ts declared and nothing implemented. */
    autoScroll?: boolean;
    /** aria-label for the floating scroll-to-bottom button. Default: "Ir al final". */
    scrollToBottomLabel?: string;
    /** Visual class for the scroll-to-bottom button (placement stays framework-owned). */
    scrollToBottomClassName?: string;
    /** Icon class for the scroll-to-bottom button. */
    scrollToBottomIconClassName?: string;
}
/**
 * B3-FIGLASS-12 — clamp long USER messages behind a "show more" disclosure
 * (ChatGPT parity: max-height + mask-image fade + aria-expanded toggle).
 * Assistant messages and the live streaming bubble are never clamped.
 */
interface CollapseProps {
    /** Default true. */
    collapseUserMessages?: boolean;
    /** Collapsed max height in px. Default 264 (11 lines at 24px leading). */
    collapseMaxHeight?: number;
    /** Disclosure copy (app-owned). Defaults: "Mostrar más" / "Mostrar menos". */
    showMoreLabel?: string;
    showLessLabel?: string;
    /** Class for the disclosure toggle button. */
    collapseToggleClassName?: string;
}
/**
 * The public props of AgentConversationSurface — the sum of every cohesive
 * capability slice above plus the one required input, the conversation state.
 * Consumers still pass a flat prop bag; the composition is a type-level concern.
 */
interface AgentConversationSurfaceProps extends SurfaceLayoutProps, SurfaceSlotProps, NewConversationProps, ComposerFrameProps, SendControlProps, MessageRenderProps, DictationProps, ImageAttachmentProps, TurnErrorProps, AutoScrollProps, CollapseProps {
    /** The conversation state + actions from `useAgentConversation`. */
    conversation: AgentConversation;
}

declare function AgentConversationSurface(props: AgentConversationSurfaceProps): react.JSX.Element;

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
    /**
     * Fire `onSelect` even when the row is already selected, so the consumer can
     * treat the click as a toggle-off (an active-project row deselects). Default
     * false — a selected row is inert (re-clicking the open conversation is a no-op).
     */
    toggleable?: boolean;
    ariaLabel?: string;
    className?: string;
}
declare function AgentSidebarItem({ selected, onSelect, title, subtitle, meta, actions, disabled, editing, toggleable, ariaLabel, className, }: AgentSidebarItemProps): react.JSX.Element;
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

export { type AgentClassNames, type AgentConversation, AgentConversationSurface, type AgentConversationSurfaceLayout, type AgentConversationSurfaceProps, type AgentIconSet, AgentPanel, type AgentPanelProps, AgentSidebarItem, type AgentSidebarItemProps, AgentSidebarSection, type AgentSidebarSectionProps, AgentWorkspaceShell, type AgentWorkspaceShellApi, type AgentWorkspaceShellDensity, type AgentWorkspaceShellProps, type AgentWorkspaceShellVisual, type AppHandledError, type AutoScrollProps, type CollapseProps, type ComposerFrameProps, DEFAULT_TURN_TIMEOUT_MS, DestructiveActionSlot, type DestructiveActionSlotProps, type DictationProps, EditableResourceItem, type EditableResourceItemProps, FI_ITEM_ACTION_CLASS, FI_ITEM_META_CLASS, FI_ITEM_SUBTITLE_CLASS, FI_ITEM_TITLE_CLASS, FI_RESOURCE_RENAME_INPUT_CLASS, FI_SECTION_CARD_CLASS, FI_SECTION_FOOTER_CLASS, FI_SECTION_HEAD_CLASS, FI_SECTION_SCROLL_CLASS, FI_SECTION_TITLE_CLASS, FI_SIDEBAR_ITEM_CLASS, FI_SIDEBAR_SECTION_CLASS, type ImageAttachmentProps, type InlineRename, ItemActionSlot, type ItemActionSlotProps, type MessageRenderProps, type NewConversationProps, type PersistError, PlanChecklist, type PlanChecklistProps, ScrollToBottomButton, type ScrollToBottomButtonProps, type SendControlProps, SourcesPanel, type SourcesPanelProps, StepsPanel, type StepsPanelProps, type SurfaceLayoutProps, type SurfaceSlotProps, type ToolCategory, type ToolVisualStatus, type TurnError, type TurnErrorProps, type UseAgentConversationOptions, type UseInlineRenameOptions, classifyTool, defaultAgentIcons, ensureDensityStyle, ensureSidebarItemStyle, ensureSidebarSectionStyle, latestOpenToolIndex, resolveIcons, shortToolName, toolIcon, toolVisualStatus, useAgentConversation, useDensityStyle, useInlineRename, useSidebarItemStyle, useSidebarSectionStyle };
