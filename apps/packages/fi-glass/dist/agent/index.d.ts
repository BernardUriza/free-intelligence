import * as react from 'react';
import { ReactNode } from 'react';
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

interface UseAgentConversationOptions {
    /** Identity of the active conversation. When it changes, the thread re-hydrates. */
    conversationId?: string | null;
    /** Messages to seed the thread with (the active conversation's stored transcript). */
    initialMessages?: ChatMessage[];
    /** Called when the thread changes from real activity (send/fold) — a persist hook. */
    onMessagesChange?: (messages: ChatMessage[]) => void;
}
interface AgentConversation {
    /** The visible thread of completed turns (user + assistant), in send order. */
    messages: ChatMessage[];
    /** The current/live turn's reduced state (for the in-flight glass-box). */
    turn: AgentTurnState;
    /** Whether a turn is actively streaming. */
    isStreaming: boolean;
    /** Send a message: pushes it optimistically, then drives the agent turn. */
    send: (text: string) => void;
    /** Clear the whole thread and reset the underlying turn/session. */
    newConversation: () => void;
}
declare function useAgentConversation(agent: AgentHook, options?: UseAgentConversationOptions): AgentConversation;

interface AgentConversationSurfaceProps {
    /** The conversation state + actions from `useAgentConversation`. */
    conversation: AgentConversation;
    /** Composer placeholder copy (app-owned). */
    composerPlaceholder?: string;
    /** Label for the new-conversation button. Default: "New chat". */
    newChatLabel?: string;
    /** Rendered when the thread is empty and idle (e.g. an app start screen). */
    emptyState?: ReactNode;
    /** Slot rendered just above the composer (e.g. an app's auth banner). */
    aboveComposer?: ReactNode;
    /** Pass-through styling/icons for the live-turn AgentPanel. */
    agentPanelProps?: Partial<Omit<AgentPanelProps, 'turn'>>;
    /** Composer wrapper class (style hook for the app). */
    composerAreaClassName?: string;
    /** Composer textarea class (style hook for the app). */
    composerTextareaClassName?: string;
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
}
declare function AgentConversationSurface({ conversation, composerPlaceholder, newChatLabel, emptyState, aboveComposer, agentPanelProps, composerAreaClassName, composerTextareaClassName, showCopyAction, renderHeader, renderBadge, renderActions, messageBubbleClassName, voiceAdapter, micSlotClassName, micButtonClassName, onVoiceError, voiceVisualizerClassName, voiceVisualizerBarClassName, }: AgentConversationSurfaceProps): react.JSX.Element;

export { type AgentClassNames, type AgentConversation, AgentConversationSurface, type AgentConversationSurfaceProps, type AgentIconSet, AgentPanel, type AgentPanelProps, PlanChecklist, type PlanChecklistProps, SourcesPanel, type SourcesPanelProps, StepsPanel, type StepsPanelProps, type ToolCategory, type ToolVisualStatus, type UseAgentConversationOptions, classifyTool, defaultAgentIcons, latestOpenToolIndex, resolveIcons, shortToolName, toolIcon, toolVisualStatus, useAgentConversation };
