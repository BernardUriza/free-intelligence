'use client';

/**
 * AgentConversationSurface — full-page agentic chat: a visible transcript above
 * the live glass-box turn, with an explicit "new conversation" control.
 *
 * This is the agentic twin of shell/ChatSurface: ChatSurface renders a ChatHook
 * (plain chat), this renders an AgentConversation (transcript + per-turn
 * glass-box). It is the framework home for DD-002 — the consumer used to
 * hand-roll this layout. Material-agnostic and app-neutral: no endpoint, token,
 * branding or backend. Apps inject those via slots (emptyState, aboveComposer)
 * and copy props.
 */

import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { useStickToBottom } from 'use-stick-to-bottom';
import type { ChatMessage, VoiceAdapter } from '@free-intelligence/core';
import { Composer } from '../composer';
import { MessageContent, MessageBubble, CopyButton } from '../messages';
import { ComposerMicSlot, AudioVisualizer, useDictation } from '../voice';
import { AgentPanel, type AgentPanelProps } from './AgentPanel';
import { ScrollToBottomButton } from './ScrollToBottomButton';
import type { AgentConversation } from './useAgentConversation';

export interface AgentConversationSurfaceProps {
  /** The conversation state + actions from `useAgentConversation`. */
  conversation: AgentConversation;
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

export function AgentConversationSurface({
  conversation,
  composerPlaceholder,
  newChatLabel = 'New chat',
  showNewChatButton = true,
  emptyState,
  aboveComposer,
  agentPanelProps,
  composerBoxClassName,
  composerAreaClassName,
  composerTextareaClassName,
  composerControlsClassName,
  showCopyAction = false,
  renderHeader,
  renderBadge,
  renderActions,
  messageBubbleClassName,
  voiceAdapter,
  micSlotClassName,
  micButtonClassName,
  onVoiceError,
  voiceVisualizerClassName,
  voiceVisualizerBarClassName,
  showSendButton = true,
  sendButtonClassName,
  sendButtonIconClassName,
  sendLabel = 'Enviar mensaje',
  composerAppend,
  onComposerAppendConsumed,
  micSlotOverride,
  errorClassName,
  retryLabel = 'Reintentar',
  dismissLabel = 'Descartar',
  retryButtonClassName,
  dismissButtonClassName,
  autoScroll = true,
  scrollToBottomLabel = 'Ir al final',
  scrollToBottomClassName,
  scrollToBottomIconClassName,
  collapseUserMessages = true,
  collapseMaxHeight,
  showMoreLabel,
  showLessLabel,
  collapseToggleClassName,
}: AgentConversationSurfaceProps) {
  const { messages, turn, isStreaming, turnError, send, retry, dismissError, newConversation } =
    conversation;
  const [input, setInput] = useState('');

  // B3-FIGLASS-12 — pin-to-bottom. The hook is called unconditionally (hooks
  // rule); when autoScroll is off the refs simply never attach, so it observes
  // nothing. isAtBottom starts true → no phantom button on first paint/SSR.
  const stick = useStickToBottom({ initial: 'instant', resize: 'smooth' });

  // B3-FIGLASS-10 — composer focus recovery. The daily-driver audit's "Enter no
  // envía": clicking the mic/send button leaves focus ON the button, so the next
  // Enter re-triggers the button instead of sending. The surface owns the
  // composer, so it owns getting focus BACK to it after voice/send/stream — via
  // the typed textareaRef (never by reaching into the composer's internal DOM).
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const refocusComposer = useCallback(() => {
    const el = inputRef.current;
    if (!el || el.disabled) return;
    // Don't fight a user who focused another text-entry surface (e.g. an app's
    // token input). Stealing from buttons/body is the whole point — that's the
    // mic/send focus trap.
    const active = document.activeElement;
    const isOtherTextEntry =
      active instanceof HTMLElement &&
      active !== el &&
      (active.tagName === 'INPUT' ||
        active.tagName === 'TEXTAREA' ||
        active.isContentEditable);
    if (isOtherTextEntry) return;
    el.focus();
  }, []);

  // B3-VOICE-OG118-6: pull-once external text injection. When composerAppend
  // becomes non-empty, append to the current input and signal the consumer to
  // reset it. The dep array intentionally omits onComposerAppendConsumed to
  // avoid re-running on every parent render; the callback is stable in practice.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!composerAppend) return;
    setInput((prev) => (prev ? `${prev} ${composerAppend}` : composerAppend));
    onComposerAppendConsumed?.();
  }, [composerAppend]);

  // Dictation (STT) — only live when the adapter can transcribe. The composer
  // text typed before recording is captured as a prefix so dictation appends to
  // it instead of clobbering it. useDictation is a no-op without `transcribe`,
  // so calling it unconditionally (hooks rule) is safe.
  const micAvailable = typeof voiceAdapter?.transcribe === 'function';
  const baseInputRef = useRef('');
  const dictation = useDictation(voiceAdapter, {
    onTranscriptUpdate: (full) => {
      const base = baseInputRef.current;
      setInput(base ? `${base} ${full}` : full);
    },
    onError: onVoiceError,
  });
  const startDictation = () => {
    baseInputRef.current = input;
    void dictation.startRecording();
  };

  // Refocus when a turn settles (clean finish, stream error, or the timeout
  // watchdog) — the textarea was disabled while streaming and focus was lost.
  // A failed turn refocuses too, so the user can edit/retry immediately.
  const wasStreaming = useRef(false);
  useEffect(() => {
    if (wasStreaming.current && !isStreaming) refocusComposer();
    wasStreaming.current = isStreaming;
  }, [isStreaming, refocusComposer]);

  // Refocus when dictation finishes transcribing: the user's next natural act is
  // Enter-to-send, but their click left focus on the mic button (the trap).
  const wasTranscribing = useRef(false);
  useEffect(() => {
    if (wasTranscribing.current && !dictation.isTranscribing) refocusComposer();
    wasTranscribing.current = dictation.isTranscribing;
  }, [dictation.isTranscribing, refocusComposer]);

  // Resolve the per-bubble class. A string applies to every role (legacy); a
  // function lets the consumer vary it per message/role. Returning undefined
  // (e.g. for an unknown role) yields no extra class — never throws.
  const resolveBubbleClass = (message: ChatMessage): string | undefined =>
    typeof messageBubbleClassName === 'function'
      ? messageBubbleClassName(message)
      : messageBubbleClassName;

  // Empty thread + nothing in flight → show the app's start screen.
  const idle =
    messages.length === 0 &&
    !isStreaming &&
    turn.status === 'thinking' &&
    !turn.plan &&
    turn.steps.length === 0 &&
    !turn.text;
  const hasThread = messages.length > 0 || isStreaming;

  const onSend = () => {
    const t = input.trim();
    if (!t) return;
    setInput('');
    send(t);
  };
  const canSend = input.trim().length > 0 && !isStreaming;

  return (
    // B3-FIGLASS-15: the ROOT is full-width — the 760px cap lives on INNER
    // content wrappers (transcript + composer), never on the scroll container,
    // so the scrollbar renders at the viewport edge like ChatGPT/AURITY /chat
    // instead of glued to the centered column.
    <div style={{ display: 'flex', flexDirection: 'column', height: '100dvh' }}>
      {/* Relative anchor: hosts the scroll area + the floating jump-to-latest
          button, so the button stays glued to the transcript's bottom edge. */}
      <div style={{ position: 'relative', flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <div
          ref={autoScroll ? stick.scrollRef : undefined}
          style={{ flex: 1, overflowY: 'auto', padding: '1.25rem 1rem' }}
        >
          <div
            ref={autoScroll ? stick.contentRef : undefined}
            style={{ maxWidth: 760, margin: '0 auto', width: '100%' }}
          >
        {idle ? (
          emptyState
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Transcript: completed turns (user + assistant), each in a bubble */}
            {messages.map((m, i) => (
              <MessageBubble
                key={i}
                role={m.role}
                header={renderHeader?.(m)}
                badge={renderBadge?.(m)}
                actions={
                  renderActions?.(m) ??
                  (showCopyAction ? <CopyButton content={m.content} /> : undefined)
                }
                className={resolveBubbleClass(m)}
              >
                <MessageContent
                  isUser={m.role === 'user'}
                  content={m.content}
                  // B3-FIGLASS-12: only USER messages clamp (ChatGPT parity) —
                  // a long pasted prompt folds behind "Mostrar más"; assistant
                  // answers always render whole.
                  collapsible={collapseUserMessages && m.role === 'user'}
                  collapsedMaxHeight={collapseMaxHeight}
                  showMoreLabel={showMoreLabel}
                  showLessLabel={showLessLabel}
                  collapseToggleClassName={collapseToggleClassName}
                />
              </MessageBubble>
            ))}

            {/* Live turn: glass-box trace stays as-is, streaming answer in a bubble */}
            {isStreaming && <AgentPanel turn={turn} {...agentPanelProps} />}
            {isStreaming && turn.text && (
              <MessageBubble
                role="assistant"
                className={resolveBubbleClass({
                  role: 'assistant',
                  content: turn.text,
                  timestamp: '',
                })}
              >
                <MessageContent isUser={false} content={turn.text} isStreaming />
              </MessageBubble>
            )}
          </div>
        )}

        {/* B3-FIGLASS-8: recoverable failure. The watchdog/error already dropped
            us out of streaming, so this replaces the zombie "thinking…" panel. */}
        {turnError && (
          <div
            role="alert"
            className={errorClassName}
            style={{
              marginTop: '1rem',
              padding: '0.75rem 1rem',
              borderRadius: 10,
              border: '1px solid rgba(248,113,113,0.35)',
              background: 'rgba(248,113,113,0.08)',
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              gap: '0.75rem',
            }}
          >
            <span style={{ color: '#fca5a5', fontSize: '0.85rem', flex: 1, minWidth: 0 }}>
              {turnError.message}
            </span>
            <button
              type="button"
              onClick={retry}
              className={retryButtonClassName}
              style={
                retryButtonClassName
                  ? undefined
                  : {
                      padding: '0.35rem 0.75rem',
                      borderRadius: 8,
                      border: '1px solid rgba(255,255,255,0.2)',
                      background: 'transparent',
                      color: '#e2e8f0',
                      fontSize: '0.8rem',
                      cursor: 'pointer',
                    }
              }
            >
              {retryLabel}
            </button>
            <button
              type="button"
              onClick={dismissError}
              className={dismissButtonClassName}
              style={
                dismissButtonClassName
                  ? undefined
                  : {
                      padding: '0.35rem 0.75rem',
                      borderRadius: 8,
                      border: 'none',
                      background: 'transparent',
                      color: '#94a3b8',
                      fontSize: '0.8rem',
                      cursor: 'pointer',
                    }
              }
            >
              {dismissLabel}
            </button>
          </div>
        )}
          </div>
        </div>
        {/* Floating jump-to-latest: only when pinning is on and the user has
            scrolled away from the bottom (use-stick-to-bottom's isAtBottom). */}
        {autoScroll && !stick.isAtBottom && (
          <ScrollToBottomButton
            onClick={() => void stick.scrollToBottom()}
            label={scrollToBottomLabel}
            className={scrollToBottomClassName}
            iconClassName={scrollToBottomIconClassName}
          />
        )}
      </div>

      <div style={{ padding: '0.75rem 1rem 1.25rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        {/* Composer column shares the transcript's 760px center cap (the
            section itself spans full width so its top border does too). */}
        <div style={{ maxWidth: 760, margin: '0 auto', width: '100%' }}>
        {hasThread && showNewChatButton && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '0.5rem' }}>
            <button
              onClick={newConversation}
              disabled={isStreaming}
              style={{
                padding: '0.35rem 0.75rem',
                borderRadius: 8,
                border: '1px solid rgba(255,255,255,0.15)',
                background: 'transparent',
                color: '#94a3b8',
                fontSize: '0.8rem',
                cursor: isStreaming ? 'not-allowed' : 'pointer',
                opacity: isStreaming ? 0.5 : 1,
              }}
            >
              {newChatLabel}
            </button>
          </div>
        )}
        {aboveComposer && (
          <div className="fi-surface-above-composer" style={{ marginBottom: '0.5rem' }}>
            {aboveComposer}
          </div>
        )}
        {/* Floating composer box — ONE container wrapping the textarea row and
            the controls row, mirroring the shell's chat-input-floating-box
            (AURITY). The canary audit found mic/send floating OUTSIDE the
            frosted box as siblings; the box structure is framework-owned so
            every consumer inherits the corrected anatomy. */}
        <div className={composerBoxClassName}>
          <Composer
            message={input}
            loading={isStreaming}
            placeholder={composerPlaceholder}
            onMessageChange={setInput}
            onSend={onSend}
            areaClassName={composerAreaClassName}
            textareaClassName={composerTextareaClassName}
            // The input fills the composer area regardless of how the consumer
            // styles it (e.g. a flex area): growth is owned here, in the
            // framework, not patched in by a consumer reaching into `.relative`.
            wrapperStyle={{ flex: '1 1 0%', minWidth: 0 }}
            // Typed focus handle (B3-FIGLASS-10): the surface refocuses the
            // input after dictation/send/stream — no internal-DOM reach.
            textareaRef={inputRef}
          />
          {(showSendButton || micSlotOverride != null || micAvailable) && (
            <div
              className={composerControlsClassName}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8 }}
            >
              {/* Built-in dictation visualizer — suppressed when micSlotOverride is used */}
              {micSlotOverride == null && micAvailable && dictation.isRecording && (
                // Live equalizer: reacts to the mic's frequency bands so the user
                // sees they're being heard. Only mounted while recording, fed by the
                // analyser the dictation hook already runs — no extra Web Audio here.
                <AudioVisualizer
                  levels={dictation.bands}
                  active={dictation.isRecording}
                  variant="bars"
                  label="Nivel del micrófono"
                  className={voiceVisualizerClassName}
                  barClassName={voiceVisualizerBarClassName}
                />
              )}
              {/* micSlotOverride replaces the built-in ComposerMicSlot + dictation */}
              {micSlotOverride != null
                ? micSlotOverride
                : micAvailable && (
                  <ComposerMicSlot
                    available
                    recording={dictation.isRecording}
                    busy={dictation.isTranscribing}
                    onStart={startDictation}
                    onStop={() => void dictation.stopRecording()}
                    className={micSlotClassName}
                    buttonClassName={micButtonClassName}
                  />
                )}
              {showSendButton && (
                // Explicit send affordance (mirrors the shell/AURITY composer). Enter
                // still sends; this is the visible button. Disabled until there's
                // trimmed text and nothing is streaming.
                <button
                  type="button"
                  onClick={onSend}
                  disabled={!canSend}
                  aria-label={sendLabel}
                  className={sendButtonClassName}
                >
                  {isStreaming ? (
                    <Loader2
                      className={
                        sendButtonIconClassName
                          ? `${sendButtonIconClassName} animate-spin`
                          : 'animate-spin'
                      }
                      aria-hidden
                    />
                  ) : (
                    <Send className={sendButtonIconClassName} aria-hidden />
                  )}
                </button>
              )}
            </div>
          )}
        </div>
        </div>
      </div>
    </div>
  );
}
