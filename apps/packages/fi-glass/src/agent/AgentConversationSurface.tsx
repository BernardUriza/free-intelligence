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

import { useRef, useState, type ReactNode } from 'react';
import type { ChatMessage, VoiceAdapter } from '@free-intelligence/core';
import { Composer } from '../composer';
import { MessageContent, MessageBubble, CopyButton } from '../messages';
import { ComposerMicSlot, AudioVisualizer, useDictation } from '../voice';
import { AgentPanel, type AgentPanelProps } from './AgentPanel';
import type { AgentConversation } from './useAgentConversation';

export interface AgentConversationSurfaceProps {
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

export function AgentConversationSurface({
  conversation,
  composerPlaceholder,
  newChatLabel = 'New chat',
  emptyState,
  aboveComposer,
  agentPanelProps,
  composerAreaClassName,
  composerTextareaClassName,
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
}: AgentConversationSurfaceProps) {
  const { messages, turn, isStreaming, send, newConversation } = conversation;
  const [input, setInput] = useState('');

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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100dvh', maxWidth: 760, margin: '0 auto' }}>
      <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem 1rem' }}>
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
                <MessageContent isUser={m.role === 'user'} content={m.content} />
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
      </div>

      <div style={{ padding: '0.75rem 1rem 1.25rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        {hasThread && (
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
        {aboveComposer}
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: micAvailable ? 8 : 0 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <Composer
              message={input}
              loading={isStreaming}
              placeholder={composerPlaceholder}
              onMessageChange={setInput}
              onSend={onSend}
              areaClassName={composerAreaClassName}
              textareaClassName={composerTextareaClassName}
            />
          </div>
          {micAvailable && dictation.isRecording && (
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
          {micAvailable && (
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
        </div>
      </div>
    </div>
  );
}
