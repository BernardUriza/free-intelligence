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

import type { ReactNode } from 'react';
import type { ChatMessage, VoiceAdapter } from '@free-intelligence/core';
import type { ComposerAction } from '../../composer';
import type { AgentPanelProps } from '../AgentPanel';
import type { AgentConversation } from '../useAgentConversation';

export type AgentConversationSurfaceLayout = 'viewport' | 'contained';

/** Root sizing behavior of the surface. */
export interface SurfaceLayoutProps {
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
export interface SurfaceSlotProps {
  /** Rendered when the thread is empty and idle (e.g. an app start screen). */
  emptyState?: ReactNode;
  /** Slot rendered just above the composer (e.g. an app's auth banner). */
  aboveComposer?: ReactNode;
}

/** The built-in new-conversation CTA above the composer. */
export interface NewConversationProps {
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
export interface SurfaceComposerProps {
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
export interface SendControlProps {
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
export interface MessageRenderProps {
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
export interface DictationProps {
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
export interface ImageAttachmentProps {
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
export interface TurnErrorProps {
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
export interface AutoScrollProps {
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
export interface CollapseProps {
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
export interface AgentConversationSurfaceProps
  extends SurfaceLayoutProps,
    SurfaceSlotProps,
    NewConversationProps,
    SurfaceComposerProps,
    SendControlProps,
    MessageRenderProps,
    DictationProps,
    ImageAttachmentProps,
    TurnErrorProps,
    AutoScrollProps,
    CollapseProps {
  /** The conversation state + actions from `useAgentConversation`. */
  conversation: AgentConversation;
}

/**
 * The exact capability slices ComposerRegion consumes — everything about the
 * box the user composes IN, plus the app slot and CTA that stack above it.
 *
 * Typing the region against this instead of the whole surface contract is what
 * makes the decomposition load-bearing rather than decorative: the compiler now
 * refuses a composer that reaches into a transcript capability
 * (`collapseMaxHeight`, `agentPanelProps`), and a new field added to an
 * unrelated slice cannot silently widen this region's surface. Still ONE object,
 * so the orchestrator never re-threads props (REGION-PROPS-1) — the slices are
 * the unit, not the field.
 */
export type ComposerRegionSurface = SurfaceSlotProps &
  NewConversationProps &
  SurfaceComposerProps &
  SendControlProps &
  DictationProps &
  ImageAttachmentProps;

/**
 * The exact capability slices TranscriptRegion consumes — message rendering,
 * the recoverable-failure banners, autoscroll and user-message collapse.
 * Same rationale as {@link ComposerRegionSurface}.
 */
export type TranscriptRegionSurface = SurfaceSlotProps &
  MessageRenderProps &
  TurnErrorProps &
  AutoScrollProps &
  CollapseProps;
