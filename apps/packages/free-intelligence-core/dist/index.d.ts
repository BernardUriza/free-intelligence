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
/**
 * MessageAuthor — WHO produced a message. Part of the contract, not app wiring.
 *
 * A shell that lets the user switch the answering persona (og118's elementos,
 * aurity's personas) renders a transcript where every bubble must say who spoke;
 * an assistant bubble with no author silently attributes the answer to the app
 * itself. That is a lie the framework must not be able to express — so the fold
 * ({@link foldAssistantTurn}) and the user capsule ({@link makeUserMessage})
 * both REQUIRE an author, and a turn can rebind it mid-stream via the `author`
 * event (the backend announces the persona it resolved for the turn).
 *
 * Only `id` and `name` are load-bearing; `symbol` and `engine` are optional
 * enrichment a shell may render as an avatar token / provenance chip.
 */
interface MessageAuthor {
    /** Stable identifier of the speaker (element id, persona id, 'user'). */
    id: string;
    /** Human name shown as the author ("Yodo", "og118", "Tú"). */
    name: string;
    /** Short avatar/badge token ("I", "og"). */
    symbol?: string | null;
    /** The engine/persona behind the answer ("Vultur", "ALICE"). */
    engine?: string | null;
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
type AgentStreamEvent$1 = {
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
    type: 'author';
    author: MessageAuthor;
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
    type: 'ping';
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
    /**
     * WHO is answering this turn, once the backend announces it (`author` event).
     * null means the backend never named a speaker — the shell then attributes the
     * turn to the agent's default author, which it must supply. See
     * {@link MessageAuthor}.
     */
    author: MessageAuthor | null;
    /**
     * How many signs of life the backend has sent while the turn was QUIET (bare
     * `ping` frames). A shell's idle watchdog re-arms on this: a healthy turn can
     * be silent for a long time (a proxied engine answers in one shot; a model
     * thinks before its first token), and killing it throws away what the user
     * wrote. A counter, not a timestamp — the reducer stays pure.
     */
    heartbeats: number;
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
declare function applyAgentEvent(state: AgentTurnState, event: AgentStreamEvent$1): AgentTurnState;

/**
 * MessageTrace — the persisted glass-box snapshot of a finished agentic turn.
 *
 * The differentiator is "see the execution, not just the result": during the
 * stream you watch the plan declared and the steps walked, but a folded message
 * historically kept only the answer text (see {@link foldAssistantTurn}). This
 * carries the agentic provenance — the declared plan with its per-step outcomes,
 * the tool calls, the evidence — INTO the durable transcript, so reloading a
 * conversation re-renders the same glass-box the live turn showed.
 *
 * Reuses the live agent contract types verbatim ({@link AgentPlan},
 * {@link ToolCall}); persistence is just a snapshot of the reduced turn state,
 * not a parallel shape. Every field is optional: a plain conversational turn
 * (no plan, no tools) folds to a message with no `trace`, unchanged.
 */
interface MessageTrace {
    /** The declared plan with per-step status/summary/outcome, if the turn planned. */
    plan?: AgentPlan;
    /** The tool calls made during the turn, if any. */
    tools?: ToolCall[];
    /** Evidence references surfaced during the turn, if any. */
    sources?: string[];
    /**
     * The model that actually produced the answer. Provenance, like the plan and
     * the tools — so it lives HERE, not in `metadata`, which persistence drops by
     * design. A "powered by <model>" chip read from `metadata` shows on the live
     * turn and vanishes on reload; read from the trace it survives.
     */
    model?: string;
}
/**
 * MessageImage — one image attached to a user message (OG118-IMAGE-UPLOAD-1).
 *
 * Base64 by design: the shells are local-first (IndexedDB / JSON records), so
 * the bytes ride inside the message instead of referencing a blob store nobody
 * runs. Producers (the composer) downscale before encoding, so a persisted
 * image stays small enough for the conversation-record size caps.
 */
interface MessageImage {
    /** MIME type of the encoded bytes, e.g. `image/jpeg`, `image/png`. */
    mediaType: string;
    /** Base64-encoded bytes — no `data:` URL prefix. */
    data: string;
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
    /** Which side of the conversation the message sits on. */
    role: 'user' | 'assistant';
    /**
     * WHO said it — the named speaker, not merely the side. A shell with a persona
     * switch (og118's elementos) must attribute each bubble to the persona that
     * actually produced it, and that attribution has to survive a reload, so it is
     * a first-class field (preserved by `sanitizeConversationMessage`, unlike
     * `metadata`). Optional only for messages authored outside the agent contract;
     * everything {@link foldAssistantTurn}/{@link makeUserMessage} builds has one.
     */
    author?: MessageAuthor;
    /** The message text. May be empty on an image-only user message. */
    content: string;
    /**
     * Images attached to this message (user messages only) — rendered in the
     * transcript and sent to the model as vision input. Absent on text-only
     * messages, so the plain case stays byte-identical to before.
     */
    images?: MessageImage[];
    /** Optional model reasoning rendered before the content. */
    thinking?: string | null;
    /** ISO 8601 timestamp. */
    timestamp: string;
    /** App-specific metadata (tone, voice, model, …). */
    metadata?: Record<string, unknown>;
    /**
     * Persisted glass-box snapshot of the agentic turn that produced this message
     * (assistant messages only). Absent for plain conversational turns and all
     * user messages — see {@link MessageTrace}.
     */
    trace?: MessageTrace;
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
 * ConversationState — the reduced state of a whole agentic CONVERSATION (the
 * thread across turns), plus the pure `applyConversationEvent` reducer that
 * derives it.
 *
 * Sibling of {@link ./state} one level up: `AgentTurnState` reduces the wire
 * events of ONE streaming turn; this reduces the lifecycle of the conversation
 * those turns live in — the optimistic push, the fold, the revert that hands the
 * user's words back, the recoverable-failure banners, persistence bookkeeping.
 *
 * WHY IT MOVED HERE (framework-first-canary, the demotion's mirror): fi-glass's
 * `useAgentConversation` held this logic across 7 `useState` + 10 `useRef` in a
 * 575-line hook, so the rules of the machine — "a failed turn must never cost
 * the user their words", "an optimistic push is not a confirmed turn" — could
 * only be exercised by mounting React and driving a fake transport. They are not
 * React rules; they are conversation rules, identical for every shell. Here they
 * are one value and one function, testable with plain assertions.
 *
 * Pure: no React, no transport, no timers, no I/O. Immutable: every event
 * returns a new state object. Time enters as an EVENT (`turn_timeout`), never as
 * a clock read — same discipline as the turn reducer's heartbeat counter.
 */

/** Why a turn failed, in terms a shell can render a recovery banner from. */
interface TurnFailure {
    kind: 'stream' | 'timeout';
    message: string;
}
/**
 * What a failed turn hands back so the shell can restore it into the composer.
 * Carries the WHOLE message: returning only the text let a shell re-send a
 * prompt whose images had silently ceased to exist.
 */
interface UnsentDraft {
    text: string | null;
    images: MessageImage[] | null;
}
/** The reduced state of the conversation. */
interface ConversationState {
    /** The visible thread. */
    messages: ChatMessage[];
    /** Set while an optimistically-pushed turn is still in flight; gates the fold. */
    pending: boolean;
    /** A recoverable turn failure the shell renders instead of a zombie panel. */
    failure: TurnFailure | null;
    /** True once a turn timed out; keeps the watchdog from re-arming on it. */
    timedOut: boolean;
    /** What a failed turn handed back, for the shell to restore. */
    unsent: UnsentDraft;
    /** The last send, replayed verbatim by a retry (text AND images). */
    lastSent: {
        text: string;
        images?: MessageImage[];
    } | null;
    /**
     * True when the current `messages` change is NOT a confirmed, settled turn
     * (the mount seed, a conversation switch, the optimistic push). A shell
     * persists only when this is false, so a failed turn never leaves a durable
     * lone user message.
     */
    skipPersist: boolean;
}
type ConversationEvent = 
/** The user sent. `controlled` shells do not get an optimistic push. */
{
    type: 'send';
    text: string;
    images?: MessageImage[];
    author: MessageAuthor;
    controlled: boolean;
}
/** The transport finished cleanly. Folds the assistant turn in. */
 | {
    type: 'turn_settled';
    turn: AgentTurnState;
    author: MessageAuthor;
    controlled: boolean;
}
/**
 * The transport reported failure. `appHandled` means the app renders its own
 * banner for this error class (e.g. a 401 token gate), so the generic
 * recoverable failure is suppressed — the revert still happens either way.
 */
 | {
    type: 'turn_failed';
    message?: string;
    controlled: boolean;
    appHandled?: boolean;
}
/** The idle watchdog fired. Time as an event keeps the reducer pure. */
 | {
    type: 'turn_timeout';
    controlled: boolean;
} | {
    type: 'dismiss_failure';
}
/** The shell restored `unsent` into its composer. */
 | {
    type: 'clear_unsent';
}
/** Load a different conversation (or start a fresh one). */
 | {
    type: 'hydrate';
    messages: ChatMessage[];
}
/** Persistence settled; the pending change is no longer un-persisted. */
 | {
    type: 'persist_settled';
};
declare function initialConversationState(seed?: ChatMessage[]): ConversationState;
/** Pure reducer: apply one conversation event, returning a new state. */
declare function applyConversationEvent(state: ConversationState, event: ConversationEvent): ConversationState;

/**
 * Transcript bridge — fold the live agentic turn into flat chat messages.
 *
 * Pure, framework-agnostic (no React, no transport). The agent contract models
 * ONE live turn (AgentTurnState); a conversation surface needs the thread as a
 * flat list. These two helpers bridge `AgentTurnState` → `ChatMessage` so any
 * shell (fi-glass and beyond) can keep a visible transcript without re-deriving
 * the mapping. Moved here from the og118 consumer (DD-002-LESSON): a reusable
 * primitive belongs in the framework, not the app wrapper.
 *
 * NO TEXT WITHOUT AN AUTHOR: both helpers take the speaker as a REQUIRED
 * argument. A shell whose user can swap the answering persona must never fold a
 * bubble the transcript cannot attribute — the alternative (an optional author
 * the consumer may forget) is exactly how og118 spent every turn claiming
 * "og118" answered while an element actually did.
 */

/** A user message, ready to render optimistically the instant the user sends.
 * `images` attaches vision input (OG118-IMAGE-UPLOAD-1); empty/absent folds to
 * the exact text-only shape every existing consumer produces. */
declare function makeUserMessage(text: string, author: MessageAuthor, images?: MessageImage[]): ChatMessage;
/**
 * Fold a finished turn's answer into an assistant message. The answer text is
 * the message content; the agentic provenance (declared plan + per-step
 * outcomes, tool calls, evidence) is snapshotted into `trace` so the durable
 * transcript re-renders the same glass-box the live turn showed — the "see the
 * execution, not just the result" differentiator survives the fold. A turn with
 * no provenance at all folds with no `trace`, unchanged.
 *
 * Model provenance rides the TRACE, not `metadata`: persistence drops metadata
 * by design (apps stash secrets there), so a model chip read from it showed on
 * the live turn and vanished on reload — a badge that was never once seen after
 * a refresh. It is provenance, and provenance persists.
 *
 * Authorship comes from the turn itself when the backend named a speaker (the
 * `author` event — the resolved persona/element); `defaultAuthor` is the agent's
 * own identity, used when it did not. Required, so the folded message always
 * knows who spoke.
 */
declare function foldAssistantTurn(turn: AgentTurnState, defaultAuthor: MessageAuthor): ChatMessage;

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
    /**
     * Images attached to THIS send (OG118-IMAGE-UPLOAD-1) — vision input for the
     * current turn. The transport forwards them to its backend as image content
     * blocks; a transport that ignores `meta` behaves exactly as before.
     */
    images?: MessageImage[];
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
 * DO NOT EDIT — generated from the fi-runner event contract.
 *
 * Source of truth: apps/packages/fi-runner/fi_runner/events.py
 * Schema:          apps/packages/fi-runner/contracts/agent-events.schema.json
 * Regenerate:      pnpm --filter @free-intelligence/core gen:events
 *
 * These are the RAW WIRE frames as fi-runner emits them (snake_case, three
 * envelope shapes). They are NOT the core AgentStreamEvent — that one is the
 * normalized, camelCase contract the reducer consumes. The translation between
 * them lives in the consumer's mapEvent, and now it maps FROM a typed wire
 * frame instead of from `Record<string, unknown>` guesswork.
 */
/**
 * The fi-runner agent stream contract. Generated from fi_runner/events.py — do not edit by hand.
 */
type AgentStreamEvent = OpenEvent | ElementEvent | TextEvent | ToolCallEvent | ResultEvent | PlanEvent | StepStartedEvent | StepDoneEvent | StepNotedEvent | PlanAmendedEvent | PlanCancelledEvent | PlanCompletedEvent | PlanFailedEvent | PlanRejectedEvent | ErrorEvent | PingEvent | DoneEvent;
/**
 * First frame of every stream. Carries the id a UI keys concurrent turns on.
 */
interface OpenEvent {
    type?: 'open';
    request_id?: string | null;
}
/**
 * Announces WHO is answering, before any token arrives.
 */
interface ElementEvent {
    type?: 'element';
    element: ElementPayload;
}
/**
 * Which persona/element answered this turn.
 *
 * ``label`` is the composed one-liner ("53 · I · Yodo"); the parts ride
 * alongside it so a UI can attribute a bubble without re-parsing that string —
 * ``name`` is the speaker's name, ``symbol`` the avatar token, ``engine`` the
 * persona/engine behind it. Optional: a runner that only knows an id/label
 * still emits a valid frame.
 */
interface ElementPayload {
    id: string;
    label: string;
    name?: string | null;
    symbol?: string | null;
    engine?: string | null;
}
/**
 * A token delta. Consumers append; they never replace.
 */
interface TextEvent {
    type?: 'text';
    text: string;
}
interface ToolCallEvent {
    type?: 'tool_call';
    tool: ToolCallPayload;
}
/**
 * One tool invocation, mirroring :class:`fi_runner.backend.ToolCall`.
 *
 * ``input`` may carry PHI and is never placed in telemetry; it stays on the
 * wire only because the glass-box panel renders it for the operator.
 */
interface ToolCallPayload {
    name: string;
    server?: string | null;
    input?: {
        [k: string]: unknown;
    } | null;
    id?: string | null;
    is_error?: boolean | null;
    duration_ms?: number | null;
}
interface ResultEvent {
    type?: 'result';
    result: TurnResultPayload;
}
/**
 * The settled result of a turn, mirroring :class:`fi_runner.backend.TurnResult`.
 *
 * ``model`` is the model that ACTUALLY ran (the retry loop may escalate to the
 * fallback), so a UI shows the answer's real provenance instead of guessing at
 * the configured default.
 */
interface TurnResultPayload {
    text: string;
    usage?: {
        [k: string]: unknown;
    } | null;
    session_id?: string | null;
    model?: string | null;
    guard_outcomes?: {
        [k: string]: unknown;
    };
    tool_calls?: ToolCallPayload[];
}
/**
 * The agent declared its plan. ``steps`` is the checklist a UI renders.
 */
interface PlanEvent {
    type?: 'plan';
    data: PlanData;
}
interface PlanData {
    steps: string[];
    session_id?: string | null;
    request_id?: string | null;
}
interface StepStartedEvent {
    type?: 'step_started';
    data: StepStartedData;
}
interface StepStartedData {
    plan_id?: string | null;
    step_index: number;
    request_id?: string | null;
}
interface StepDoneEvent {
    type?: 'step_done';
    data: StepDoneData;
}
/**
 * ``summary`` accompanies a ``done`` step; ``error`` a failed/cancelled one.
 */
interface StepDoneData {
    plan_id?: string | null;
    step_index: number;
    status: 'done' | 'failed' | 'cancelled';
    summary?: string | null;
    error?: string | null;
    request_id?: string | null;
}
interface StepNotedEvent {
    type?: 'step_noted';
    data: StepNotedData;
}
interface StepNotedData {
    plan_id?: string | null;
    step_index: number;
    note: string;
    request_id?: string | null;
}
interface PlanAmendedEvent {
    type?: 'plan_amended';
    data: PlanAmendedData;
}
interface PlanAmendedData {
    plan_id?: string | null;
    action: 'insert' | 'replan';
    request_id?: string | null;
}
interface PlanCancelledEvent {
    type?: 'plan_cancelled';
    data: PlanCancelledData;
}
interface PlanCancelledData {
    plan_id?: string | null;
    reason?: string;
    request_id?: string | null;
}
interface PlanCompletedEvent {
    type?: 'plan_completed';
    data: PlanTerminalData;
}
/**
 * Counters for the terminal plan frame.
 *
 * They default to ``0`` rather than being optional on purpose: a consumer must
 * never receive ``undefined`` here and coerce it silently. The emitter fills
 * real counts whenever the observer ran.
 */
interface PlanTerminalData {
    plan_id?: string | null;
    completed_count?: number;
    failed_count?: number;
    cancelled_count?: number;
    request_id?: string | null;
}
interface PlanFailedEvent {
    type?: 'plan_failed';
    data: PlanTerminalData;
}
interface PlanRejectedEvent {
    type?: 'plan_rejected';
    data: PlanRejectedData;
}
/**
 * A plan guard refused the declared plan before any step ran.
 */
interface PlanRejectedData {
    reason: string;
    matched?: GuardMatch[];
    reinforcement?: string | null;
    guard?: string | null;
    request_id?: string | null;
}
interface GuardMatch {
    index: number;
    label: string;
    [k: string]: unknown;
}
/**
 * The turn died. Terminal — no ``done`` follows a fatal error.
 */
interface ErrorEvent {
    type?: 'error';
    message: string;
}
/**
 * A sign of life while the turn is QUIET.
 *
 * A client's idle watchdog cannot tell "the model is thinking" from "the
 * backend hung" — both look like silence. And silence is normal here: a turn
 * proxied to an external engine emits NOTHING until the whole answer lands
 * (up to 95s), while a local turn can think far longer than a token gap.
 * Without this frame the client kills healthy turns and throws away what the
 * user wrote. The ping carries nothing; its arrival IS the signal.
 */
interface PingEvent {
    type?: 'ping';
}
/**
 * Last frame of a healthy stream.
 */
interface DoneEvent {
    type?: 'done';
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
    /** ISO 8601 timestamp of when the user pinned this conversation. Absent ⇒ not
     * pinned. A timestamp (not a boolean) so the pinned section orders by
     * last-pinned first without a separate counter. */
    pinnedAt?: string;
    /** ISO 8601 timestamp of when the user archived this conversation. Absent ⇒
     * active. Archiving is the reversible alternative to delete: the record keeps
     * its messages and moves to the archived section. */
    archivedAt?: string;
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
    pinnedAt?: string;
    archivedAt?: string;
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
 * Reduce a ChatMessage to the fields safe to persist: role, author, content,
 * timestamp, plus the glass-box `trace` when present (B3-FIGLASS-TRACE-
 * PERSISTENCE-1).
 *
 * Privacy by structure: `metadata` is DROPPED on purpose — apps stuff secrets
 * there (a `Bearer` token, tool payloads), so it must never reach durable
 * storage. `trace` and `author` are the deliberate exceptions, not holes in that
 * boundary: both carry only non-sensitive, already-user-visible provenance —
 * plan-step labels/summaries (model-authored, rendered live), tool NAMES (core's
 * ToolCall is {id,name,server,isError} — no arguments/payloads), source URLs,
 * and the public name of the persona that spoke. Persisting what the live turn
 * already showed leaks nothing new — and dropping the author would re-anonymize
 * every bubble on reload, which is the bug the contract exists to prevent.
 * Included only when present, so a plain message stays minimal; id, thinking and
 * metadata are still dropped by construction.
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
/**
 * Pin or unpin a record. Pinning stamps `pinnedAt` (the pinned section orders by
 * last-pinned first) and lifts the record out of the archive — a pin is an
 * explicit "keep this in front of me", incompatible with archived. Unpinning
 * drops the field entirely. `updatedAt` is deliberately NOT touched: pinning is
 * organization, not content, and must not fake recency in the active list.
 */
declare function setConversationPinned(record: ConversationRecord, pinned: boolean, now?: string): ConversationRecord;
/**
 * Archive or unarchive a record. Archiving stamps `archivedAt` and clears any
 * pin (an archived conversation cannot stay in the pinned section). Unarchiving
 * drops the field and the record rejoins the active list at its own
 * `updatedAt` — which, like pinning, is deliberately not touched.
 */
declare function setConversationArchived(record: ConversationRecord, archived: boolean, now?: string): ConversationRecord;
/** Project a record to its light summary — excludes `messages`. */
declare function summarizeConversation(record: ConversationRecord): ConversationSummary;
/**
 * Filter summaries by a free-text query over title + preview (CONV-SEARCH-1).
 * Case- and diacritic-insensitive; every whitespace-separated term must match
 * somewhere (AND semantics). An empty/whitespace query returns the input
 * untouched. Pure — feed the result to {@link organizeConversationSummaries}.
 */
declare function filterConversationSummaries(summaries: ConversationSummary[], query: string): ConversationSummary[];
/** The sidebar's three sections, each already in display order. */
interface OrganizedConversations {
    /** Pinned, last-pinned first. */
    pinned: ConversationSummary[];
    /** Neither pinned nor archived, most recently updated first. */
    active: ConversationSummary[];
    /** Archived, most recently archived first. */
    archived: ConversationSummary[];
}
/**
 * Split summaries into the pinned / active / archived sections every sidebar
 * renders. Pure and total: a summary lands in exactly one section (`archivedAt`
 * wins over a stray `pinnedAt`, though the pin/archive transformers never
 * produce that state). ISO 8601 timestamps sort lexicographically.
 */
declare function organizeConversationSummaries(summaries: ConversationSummary[]): OrganizedConversations;

export { type AgentHook, type AgentMeta, type AgentPlan, type AgentSendMeta, type AgentStreamEvent$1 as AgentStreamEvent, type AgentTurnState, type AgentTurnStatus, type AgentStreamEvent as AgentWireEvent, type AudioSource, CONVERSATION_SCHEMA_VERSION, type ChatHook, type ChatMessage, type ChatStreamingState, type ConversationEvent, type ConversationLibrary, type ConversationRecord, type ConversationState, type ConversationSummary, type CreateConversationRecordArgs, type GuardLevel, type GuardRejection, type MessageAuthor, type MessageImage, type MessageTrace, type OrganizedConversations, type PlanOutcome, type PlanStep, type StepStatus, type ThemeTokens, type ToolCall, type TranscribeContext, type TranscriptResult, type TurnFailure, type UnsentDraft, type VoiceAdapter, type VoiceOption, type DoneEvent as WireDoneEvent, type ElementEvent as WireElementEvent, type ErrorEvent as WireErrorEvent, type OpenEvent as WireOpenEvent, type PlanAmendedEvent as WirePlanAmendedEvent, type PlanCancelledEvent as WirePlanCancelledEvent, type PlanCompletedEvent as WirePlanCompletedEvent, type PlanEvent as WirePlanEvent, type PlanFailedEvent as WirePlanFailedEvent, type PlanRejectedEvent as WirePlanRejectedEvent, type ResultEvent as WireResultEvent, type StepDoneEvent as WireStepDoneEvent, type StepNotedEvent as WireStepNotedEvent, type StepStartedEvent as WireStepStartedEvent, type TextEvent as WireTextEvent, type ToolCallEvent as WireToolCallEvent, applyAgentEvent, applyConversationEvent, createConversationRecord, deriveConversationPreview, deriveConversationTitle, filterConversationSummaries, foldAssistantTurn, initialAgentTurnState, initialConversationState, makeUserMessage, organizeConversationSummaries, renameConversationRecord, resolveConversationTitle, sanitizeConversationMessage, setConversationArchived, setConversationPinned, summarizeConversation };
