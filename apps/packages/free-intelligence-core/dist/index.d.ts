/**
 * ThemeTokens — the material-agnostic slot contract for a frosted-surface theme.
 *
 * Every `fi-<material>` skin (fi-glass today; future fi-slate, fi-paper, …) fills
 * these same slots with its own values. Consumers — fi-glass's shell/agentic
 * components and the apps themselves — depend only on this shape, never on a
 * concrete material. That is precisely what makes "material = token swap" hold
 * without any material having to depend on another.
 *
 * This is pure data: no React, no styling, no logic. It lives in core so a future
 * material never has to reach into fi-glass just to learn the slot shape.
 */
interface ThemeTokens {
    /** Backdrop blur radius for frosted surfaces, e.g. `"12px"`. */
    blur: string;
    /** Reduced blur radius for small viewports (≤768px), e.g. `"8px"`. */
    blurCompact: string;
    /** Surface fill opacity, `0..1`. */
    opacity: number;
    /** Backdrop saturation boost, e.g. `"180%"`. */
    saturation: string;
    /** Light surface base fill as an `"r, g, b"` triple, e.g. `"255, 255, 255"`. */
    surfaceLight: string;
    /** Light surface border (full CSS color), e.g. `"rgba(255, 255, 255, 0.18)"`. */
    borderLight: string;
    /** Dark surface fill (full CSS color), e.g. `"rgba(15, 23, 42, 0.7)"`. */
    surfaceDark: string;
    /** Dark surface border (full CSS color), e.g. `"rgba(148, 163, 184, 0.2)"`. */
    borderDark: string;
}

/**
 * Audio produced by synthesize().
 *
 * - `Blob`        → a fully-rendered clip; fi-glass calls URL.createObjectURL.
 * - `{ url }`     → a ready (possibly streaming) URL; fi-glass uses it directly.
 *
 * Supporting both keeps streaming TTS (hear-while-generating) open without
 * forcing every backend to stream.
 */
type AudioSource = Blob | {
    url: string;
};
/** A selectable TTS voice offered by the adapter. */
interface VoiceOption {
    /** Stable id passed back to synthesize() (e.g. "nova", "en-US-AvaNeural"). */
    id: string;
    /** Human label for the picker (e.g. "Nova"). */
    label: string;
    /** Optional group header for the picker (e.g. "OpenAI", "Azure Neural"). */
    group?: string;
}
/** Result of transcribing one recorded audio chunk. */
interface TranscriptResult {
    /** Recognized text for this chunk (may be empty). */
    text: string;
}
/** Metadata fi-glass passes alongside each transcription chunk. */
interface TranscribeContext {
    /**
     * 0-based index of this chunk within the current recording. A streaming
     * adapter uses it for session/ordering; a one-shot adapter (single chunk on
     * stop) simply ignores it.
     */
    index: number;
    /** Lets the app abort the in-flight request when recording stops. */
    signal?: AbortSignal;
}
/**
 * VoiceAdapter — the app's voice engine, injected whole into fi-glass.
 *
 * Capabilities are a la carte (all members optional):
 *   - no adapter          -> no voice (UI hides mic + speak)
 *   - synthesize present  -> TTS available (SpeakButton + AudioPlayer)
 *   - transcribe present  -> STT available (VoiceMicButton dictation)
 *
 * Add a new capability by adding an optional member here — never by threading a
 * new callback through the components.
 */
interface VoiceAdapter {
    /** Synthesize speech for `text` in an optional voice id; resolves to audio. */
    synthesize?(text: string, voice?: string): Promise<AudioSource>;
    /** Voices offered in the player's picker. */
    readonly availableVoices?: VoiceOption[];
    /** Voice id used when the caller doesn't specify one. */
    readonly defaultVoice?: string;
    /** Transcribe one recorded audio chunk to text. */
    transcribe?(chunk: Blob, ctx?: TranscribeContext): Promise<TranscriptResult>;
}

/**
 * ChatMessage — the material-agnostic shape of one chat message.
 *
 * Apps may use a richer message type (e.g. aurity's FIMessage with typed
 * metadata); ChatHook is generic over the message type and defaults to this.
 * Pure data — no React, no styling.
 */
interface ChatMessage {
    /** Stable id (optional for transient/streaming messages). */
    id?: string;
    /** Who authored the message. */
    role: 'user' | 'assistant';
    /** The message text. */
    content: string;
    /** Optional model reasoning rendered before the content. */
    thinking?: string | null;
    /** ISO 8601 timestamp. */
    timestamp: string;
    /** App-specific metadata (tone, voice, model, …). */
    metadata?: Record<string, unknown>;
}
/** Streaming state surfaced by a ChatHook while a response is in flight. */
interface ChatStreamingState {
    status: 'idle' | 'connecting' | 'streaming' | 'thinking' | 'complete' | 'error' | 'aborted';
    content: string;
    thinking: string;
    isStreaming: boolean;
}

/**
 * ChatHook — the conversation contract the fi-glass shell consumes.
 *
 * This is the dependency-inversion spine of the chat shell: ChatWidget never
 * imports a concrete conversation hook, it consumes this interface. aurity
 * implements it with `useFIConversation`; og118 implements its own against its
 * backend. A fat contract (state + actions + streaming) → it earns a place in
 * core (unlike navigation, which is a plain callback prop).
 *
 * Generic over:
 * - `TMessage` — the message type (aurity passes its FIMessage; default ChatMessage).
 * - `TNode`    — the UI-slot node type (aurity passes React's ReactNode). Kept
 *   generic so core stays framework-agnostic (no React import).
 */
interface ChatHook<TMessage = ChatMessage, TNode = unknown> {
    messages: TMessage[];
    loading: boolean;
    isTyping: boolean;
    loadingInitial?: boolean;
    hasMoreMessages?: boolean;
    loadingOlder?: boolean;
    streamingMessage?: string;
    streaming?: ChatStreamingState;
    sendMessage: (message: string, metadata?: object) => Promise<void>;
    sendMessageStream?: (message: string, metadata?: object) => Promise<void>;
    loadOlderMessages?: () => Promise<void>;
    clearConversation?: () => void;
    getIntroduction?: () => void;
    startConversation?: () => Promise<void>;
    sendQuickReply?: (reply: string) => Promise<void>;
    conversationState?: {
        quickReplies?: string[];
        actions?: Array<{
            type: string;
            data: unknown;
        }>;
        metadata?: Record<string, unknown>;
    };
    customEmptyState?: TNode;
    customQuickReplies?: TNode;
}

/**
 * AgentStreamEvent — the agent-turn wire contract.
 *
 * Material-agnostic, React-free, and intentionally NOT shaped to any one app's
 * backend. Each app's hook MAPS its real stream onto this union: insult_ai maps
 * its `/chat/stream` SSE frames; og118 maps its own transport; a fi-runner-native
 * hook would map `turn_flow` / `ToolCall` / task_tracker stream events. The
 * fi-glass agent panels and the pure `applyAgentEvent` reducer consume ONLY this
 * union — never a concrete transport, endpoint, or auth.
 *
 * This is the neutral middle: it equals neither insult_ai's frontend shape nor
 * fi-core's task_tracker shape; both map onto it. It is the most consequential
 * contract in the fi-glass roadmap — og118 and every future app inherit it.
 */
/** Lifecycle status of a single planned step. */
type StepStatus = 'pending' | 'running' | 'done' | 'failed' | 'cancelled';
/** Severity a guard can assign. Generic — each app names its own guards. */
type GuardLevel = 'ok' | 'warning' | 'critical';
/** A tool invocation surfaced for the live audit trail. */
interface ToolCall {
    /** Stable id from the provider (e.g. tool_use_id); null while pending. */
    id: string | null;
    /** Tool identifier as the agent named it. */
    name: string;
    /** Originating server/namespace, or null for built-ins. */
    server: string | null;
    /** null = pending, false = ok, true = errored. */
    isError: boolean | null;
}
/**
 * A soft guard decision against the declared plan (the stream continues).
 *
 * Core defines the SHAPE of the verdict — not what any guard evaluates. The
 * `reason`/copy is owned by the app; core only carries that a guardrail
 * assessed the plan and emitted a verdict. This is the universal agentic-safety
 * pattern, not a domain concept.
 */
interface GuardRejection {
    /** Human-readable reason. App owns the wording/copy. */
    reason: string;
    /** Which plan steps tripped the guard. */
    matched: Array<{
        index: number;
        label: string;
    }>;
    /** Guard identifier (app-defined), or null. */
    guard: string | null;
}
/** Per-turn observability. All optional; each app fills what it has. */
interface AgentMeta {
    requestId?: string | null;
    latencyMs?: number | null;
    toolCount?: number | null;
    tokens?: Record<string, unknown> | null;
    /** Worst-case guard verdicts by guard name. */
    guardLevels?: Record<string, GuardLevel> | null;
    attempts?: number | null;
    model?: string | null;
}
/**
 * The discriminated union an app's hook emits as a turn unfolds.
 *
 * `plan` carries flat labels (the initial announcement, no status yet); the rich
 * per-step state (PlanStep) is built by the reducer as `step_started`/`step_done`
 * arrive — the separation between "what was announced" and "what has happened".
 *
 * `result.sources` is the generic name for evidence references (e.g. source URLs
 * from RAG or web-search). Apps extract them however they like (insult_ai parses
 * a "Receipts" markdown tail in its own hook — app-specific, stays there).
 */
type AgentStreamEvent = {
    type: 'open';
    sessionId?: string;
    requestId?: string;
} | {
    type: 'plan';
    steps: string[];
} | {
    type: 'plan_rejected';
    rejection: GuardRejection;
} | {
    type: 'step_started';
    index: number;
} | {
    type: 'step_done';
    index: number;
    status: 'done' | 'failed' | 'cancelled';
    summary?: string;
    error?: string;
} | {
    type: 'step_noted';
    index: number;
    note: string;
} | {
    type: 'plan_amended';
    action: 'insert' | 'replan';
} | {
    type: 'plan_cancelled';
    reason?: string;
} | {
    type: 'plan_completed';
    completedCount?: number;
    failedCount?: number;
    cancelledCount?: number;
} | {
    type: 'plan_failed';
    completedCount?: number;
    failedCount?: number;
    cancelledCount?: number;
} | {
    type: 'tool_call';
    call: ToolCall;
} | {
    type: 'text';
    delta: string;
} | {
    type: 'result';
    text: string;
    sources?: string[];
    meta?: AgentMeta;
} | {
    type: 'meta';
    meta: AgentMeta;
} | {
    type: 'error';
    message: string;
} | {
    type: 'done';
};

/**
 * AgentTurnState — the reduced state the fi-glass agent panels render, plus the
 * pure `applyAgentEvent` reducer that derives it from the wire stream.
 *
 * The reducer is pure (no React, no transport, no I/O) so every app reuses the
 * same event→state logic and only supplies the transport that produces the
 * AgentStreamEvent stream. Immutable: every event returns a new state object.
 */

/** One step of the declared plan, enriched with live status. */
interface PlanStep {
    label: string;
    status: StepStatus;
    summary?: string;
    error?: string;
    /** Free-text annotation from note_step (carried by the step_noted event). */
    note?: string;
}
/** Terminal verdict of a whole plan (finalize_plan / cancel_plan). */
type PlanOutcome = 'completed' | 'failed' | 'cancelled';
/** The agent's declared plan. Guard-as-quality: rejection is woven in here. */
interface AgentPlan {
    steps: PlanStep[];
    /** Set when a guard blocks; cleared when a fresh plan is declared. */
    rejection?: GuardRejection | null;
    /**
     * Set when the agent restructures the plan mid-turn (plan_amended). 'replan'
     * is then followed by a fresh `plan` event that reseeds steps and clears this.
     */
    amended?: 'insert' | 'replan' | null;
    /** Terminal plan verdict once finalize_plan / cancel_plan settles it. */
    outcome?: PlanOutcome | null;
}
type AgentTurnStatus = 'thinking' | 'streaming' | 'done' | 'error';
/** The full reduced state of one agentic turn. */
interface AgentTurnState {
    plan: AgentPlan | null;
    steps: ToolCall[];
    text: string;
    /** Evidence references (e.g. source URLs). App-agnostic name. */
    sources: string[];
    meta: AgentMeta | null;
    status: AgentTurnStatus;
    errorMessage?: string;
}
/** A fresh, empty turn — call at the start of each agentic turn. */
declare function initialAgentTurnState(): AgentTurnState;
/**
 * Pure reducer: apply one wire event to the turn state, returning a new state.
 *
 * Mirrors the universal turn lifecycle; an app's hook feeds it the events its
 * transport produces. Unknown/transport-only events (`open`) pass through
 * untouched.
 */
declare function applyAgentEvent(state: AgentTurnState, event: AgentStreamEvent): AgentTurnState;

/**
 * Transcript bridge — fold the live agentic turn into flat chat messages.
 *
 * Pure, framework-agnostic (no React, no transport). The agent contract models
 * ONE live turn (AgentTurnState); a conversation surface needs the thread as a
 * flat list. These two helpers bridge `AgentTurnState` → `ChatMessage` so any
 * shell (fi-glass and beyond) can keep a visible transcript without re-deriving
 * the mapping. Moved here from the og118 consumer (DD-002-LESSON): a reusable
 * primitive belongs in the framework, not the app wrapper.
 */

/** A user message, ready to render optimistically the instant the user sends. */
declare function makeUserMessage(text: string): ChatMessage;
/**
 * Fold a finished turn's answer into an assistant message. Keeps only the
 * material-agnostic content (no AgentTurnState snapshot) — a future gate can add
 * per-turn glass-box rendering without bloating the ChatMessage contract now.
 * Model provenance survives the fold: `turn.meta.model` lands in
 * `metadata.model` so a shell's badge slot ("Powered by …") has real data after
 * persistence, not just during the live turn.
 */
declare function foldAssistantTurn(turn: AgentTurnState): ChatMessage;

/**
 * Per-send metadata the conversation layer may hand the transport. Optional and
 * backward-compatible — a transport that ignores it behaves exactly as before.
 */
interface AgentSendMeta {
    /**
     * The confirmed conversation so far (prior user/assistant turns, NOT the
     * message being sent). A transport with a stateless/storeless backend replays
     * this for continuity — the og118 canary: the durable transcript lives in the
     * client (IndexedDB), so continuity survives a recycled backend. It is
     * conversational CONTEXT only; the backend re-sanitizes it and never treats it
     * as authorization.
     */
    history?: ChatMessage[];
}
/**
 * AgentHook — the agentic-turn contract the fi-glass agent panels consume.
 *
 * Dependency-inversion spine, twin of ChatHook. The app implements it against
 * its own transport (insult_ai: POST /chat/stream SSE → applyAgentEvent;
 * og118: its own). fi-glass NEVER imports the transport, endpoints, or auth.
 *
 * This is DATA + ACTIONS only. Presentation slots (renderSources /
 * renderGuardBanner / icons) live on the AgentPanel props in fi-glass, NOT here
 * — the hook is data, the panel is render. (Cleaner than Curio's ChatHook, which
 * carried customEmptyState.) Because no member references a UI node type, the
 * hook needs no `TNode` generic; only the panel is generic over its node type.
 */
interface AgentHook {
    /** Current/last turn's reduced state. */
    turn: AgentTurnState;
    /** Whether a turn is actively streaming. */
    isStreaming: boolean;
    /** Start an agentic turn. `meta.history` lets the conversation layer replay
     * prior turns for continuity on a storeless backend (see {@link AgentSendMeta}). */
    send: (message: string, meta?: AgentSendMeta) => Promise<void>;
    /** Abort the in-flight turn, if supported. */
    abort?: () => void;
    /** Reset the session/turn. */
    reset?: () => void;
}

/**
 * ConversationRecord — the persisted shape of one local-first conversation.
 *
 * DD-002B1: og118 (and every future fi-glass shell) needs the transcript to
 * survive a refresh and a list of past chats for a sidebar. The record is the
 * unit a ConversationLibrary stores; the summary is the light row a sidebar
 * lists without paying for the full message array. Pure data — no React, no
 * browser, no transport. The `id` doubles as the backend session_id so the
 * local transcript and the server's conversation store key the same thread.
 */

interface ConversationRecord {
    /** Stable id. Doubles as the backend session_id for the same thread. */
    id: string;
    /** Human-readable title. Derived from the first user message unless the user
     * renamed it, in which case `titleCustom` is set and the title is preserved
     * across future message persists. */
    title: string;
    /** True when the user explicitly renamed this conversation. A custom title is
     * never re-derived from messages on persist. Absent/false ⇒ auto-derived. */
    titleCustom?: boolean;
    /** ISO 8601 creation timestamp. */
    createdAt: string;
    /** ISO 8601 timestamp of the last change. */
    updatedAt: string;
    /** The thread, sanitized for storage (role/content/timestamp only). */
    messages: ChatMessage[];
    /** Snippet of the last non-empty message, for the sidebar. */
    preview: string;
    /** Schema version of this record, for forward migrations. */
    schemaVersion: number;
}
/** A light row for listing conversations in a sidebar (no messages). */
interface ConversationSummary {
    id: string;
    title: string;
    createdAt: string;
    updatedAt: string;
    preview: string;
}

/**
 * ConversationLibrary — the storage contract for local-first conversations.
 *
 * A pure async interface: adapters implement it over IndexedDB (fi-glass), a
 * backend, or filesystem (later layers) without core taking a dependency on any
 * of them. `list` returns light summaries (cheap); `get` hydrates one full
 * record; `put` upserts; `delete`/`clear` remove. Keeping the contract in core
 * is what stops a reusable persistence primitive from being trapped in a
 * consumer app (DD-002-LESSON / framework-first-canary).
 */

interface ConversationLibrary {
    /** All conversations as light summaries, newest `updatedAt` first. */
    list(): Promise<ConversationSummary[]>;
    /** The full record for `id`, or `null` if none. */
    get(id: string): Promise<ConversationRecord | null>;
    /** Insert or replace a record by its `id`. */
    put(record: ConversationRecord): Promise<void>;
    /** Remove the record for `id` (no-op if absent). */
    delete(id: string): Promise<void>;
    /** Remove every stored conversation. */
    clear(): Promise<void>;
}

/**
 * Conversation helpers — pure, deterministic primitives for building and
 * summarizing ConversationRecords. No React, no browser, no transport.
 *
 * Privacy by structure: `sanitizeConversationMessage` builds a NEW message with
 * exactly the allowed subset (role / content / timestamp). Any other field a
 * ChatMessage may carry now or later — `id`, `thinking`, `metadata`, a future
 * tool payload or token — is dropped by construction, not by an allow/deny list
 * someone must remember to update. The initial privacy guarantee is the
 * restriction, not PII heuristics.
 *
 * Determinism: helpers that stamp a time accept an optional `now` so tests are
 * reproducible; they fall back to the wall clock only when it is omitted.
 */

/** Schema version stamped on every record created here. */
declare const CONVERSATION_SCHEMA_VERSION = 1;
/**
 * Reduce a ChatMessage to the only fields safe to persist: role, content, and
 * timestamp. Drops id, thinking, metadata, and anything else by construction.
 */
declare function sanitizeConversationMessage(message: ChatMessage): ChatMessage;
/** Title from the first non-empty user message; `DEFAULT_TITLE` otherwise. */
declare function deriveConversationTitle(messages: ChatMessage[], max?: number): string;
/** Preview from the last non-empty message of any role; `''` otherwise. */
declare function deriveConversationPreview(messages: ChatMessage[], max?: number): string;
/** Arguments for {@link createConversationRecord}. */
interface CreateConversationRecordArgs {
    /** Stable id (doubles as the backend session_id). */
    id: string;
    /** Initial thread; sanitized before storing. Default: empty. */
    messages?: ChatMessage[];
    /** ISO timestamp to stamp createdAt/updatedAt. Default: now. */
    now?: string;
}
/** Build a fresh, sanitized record with derived title + preview. */
declare function createConversationRecord(args: CreateConversationRecordArgs): ConversationRecord;
/**
 * Resolve the title to stamp when persisting messages: a user-set (custom)
 * title is preserved; otherwise it is derived from the messages. This is the
 * SSOT that keeps `persist` from clobbering a rename on the next message.
 */
declare function resolveConversationTitle(messages: ChatMessage[], prev?: {
    title: string;
    titleCustom?: boolean;
}): string;
/**
 * Apply a user rename to a record. A non-empty title is stored verbatim
 * (trimmed, whitespace-collapsed, capped at TITLE_MAX) and marks the record
 * `titleCustom` so future persists never re-derive it. An empty/whitespace
 * title reverts to the derived title and clears the custom flag
 * (emptyTitlePolicy: revert-to-derived). Pure — stamps `updatedAt` from `now`.
 */
declare function renameConversationRecord(record: ConversationRecord, rawTitle: string, now?: string): ConversationRecord;
/** Project a record to its light summary — excludes `messages`. */
declare function summarizeConversation(record: ConversationRecord): ConversationSummary;

export { type AgentHook, type AgentMeta, type AgentPlan, type AgentSendMeta, type AgentStreamEvent, type AgentTurnState, type AgentTurnStatus, type AudioSource, CONVERSATION_SCHEMA_VERSION, type ChatHook, type ChatMessage, type ChatStreamingState, type ConversationLibrary, type ConversationRecord, type ConversationSummary, type CreateConversationRecordArgs, type GuardLevel, type GuardRejection, type PlanOutcome, type PlanStep, type StepStatus, type ThemeTokens, type ToolCall, type TranscribeContext, type TranscriptResult, type VoiceAdapter, type VoiceOption, applyAgentEvent, createConversationRecord, deriveConversationPreview, deriveConversationTitle, foldAssistantTurn, initialAgentTurnState, makeUserMessage, renameConversationRecord, resolveConversationTitle, sanitizeConversationMessage, summarizeConversation };
