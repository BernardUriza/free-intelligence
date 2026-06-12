'use client';

/**
 * og118 agentic chat — the glass-box surface, now local-first (DD-002B1.3).
 *
 * B3-VOICE-OG118-6: durable audio queue adoption. The in-composer mic no longer
 * auto-transcribes on stop; instead it saves to a local IndexedDB queue
 * (useDurableRecording). The user reviews the queue and transcribes explicitly
 * (useAudioQueue). On success the transcript lands in the composer via the
 * surface's composerAppend prop. The direct-dictation voiceAdapter is replaced
 * by micSlotOverride in the composer row.
 *
 * og118 supplies only the app-specific pieces: the TRANSPORT (useOg118Agent),
 * the access-token banner, branding/copy, the start screen, and the chat
 * sidebar. The reusable machinery — visible transcript, optimistic user message,
 * assistant fold, live AgentPanel, AND local-first persistence — lives in the
 * framework (fi-glass `useAgentConversation` + `useConversationLibrary` +
 * `IndexedDBConversationLibrary`). DD-002-LESSON: the consumer consumes the
 * primitive; it does not re-implement it.
 *
 * Identity: the conversation library owns the active id, which IS the backend
 * session_id (passed to useOg118Agent). One id ⇒ the local transcript and the
 * server's conversation store key the same thread, so a refresh keeps both the
 * visible transcript (IndexedDB) and intra-deploy model continuity.
 */

import { useState } from 'react';
import { Loader2, Pause, Play, Square } from 'lucide-react';
import { AgentConversationSurface, useAgentConversation } from 'fi-glass/agent';
import {
  IndexedDBConversationLibrary,
  useConversationLibrary,
} from 'fi-glass/conversation';
import {
  useVoice,
  RichAudioPlayer,
  AudioQueueStore,
  useDurableRecording,
  useAudioQueue,
  AudioQueuePanel,
  ComposerMicSlot,
  AudioVisualizer,
} from 'fi-glass/voice';
import { useOg118Agent } from '@/lib/useOg118Agent';
import { getToken, setToken, AUTH401 } from '@/lib/og118Token';
import { og118VoiceAdapter } from '@/lib/og118VoiceAdapter';
import { Og118StartScreen } from './Og118StartScreen';
import { Og118Sidebar } from './Og118Sidebar';
import { Og118MessageActions } from './Og118MessageActions';

// Module-level singletons. Constructors are SSR-safe (they store config only,
// never touch IndexedDB), so one stable instance shared across renders and
// remounts is correct and avoids reopening the database.
const conversationLibrary = new IndexedDBConversationLibrary();
const audioQueueStore = new AudioQueueStore();

export function Og118AgentChat() {
  const lib = useConversationLibrary(conversationLibrary);
  const agent = useOg118Agent(lib.activeId);
  const conversation = useAgentConversation(agent, {
    conversationId: lib.activeId,
    initialMessages: lib.activeMessages,
    onMessagesChange: lib.persist,
    // 401 is og118's own error class — the token-gate banner (needsAuth) handles
    // it, and a blind retry would just 401 again. Claim it so the framework's
    // generic recoverable banner does not double up. Everything else (timeouts,
    // stream death) still surfaces generically.
    isAppHandledError: (t) => (t.errorMessage ?? '').startsWith(AUTH401),
  });
  const [tokenInput, setTokenInput] = useState(() => getToken() ?? '');
  // Voice errors (STT recording errors + transcription failures) are surfaced to
  // the user via a dismissable banner. The adapter only emits controlled error
  // messages (no tokens, no PHI, no stack), so the string is safe to render verbatim.
  const [voiceError, setVoiceError] = useState<string | null>(null);
  // Pull-once composer injection: when a durable-queue transcription succeeds, the
  // text lands here; AgentConversationSurface appends it and calls the consumed
  // callback, which resets this state back to ''.
  const [composerAppend, setComposerAppend] = useState('');
  const { turn } = conversation;

  // TTS consumer wiring (B3-TTS-1): synthesis goes through og118's adapter
  // (backend /tts/synthesize); fi-glass owns playback + object-URL lifecycle.
  // No audio state lives in og118 — useVoice resolves the Blob to a URL and
  // AudioPlayer plays it.
  const voice = useVoice(og118VoiceAdapter, {
    onError: (e, ctx) => console.error('[og118] tts', ctx, e),
  });

  // B3-VOICE-OG118-6: durable local audio capture.
  // useDurableRecording owns the mic + IndexedDB save; useAudioQueue owns
  // transcription + queue management. og118 owns only the transport (adapter).
  const recording = useDurableRecording({
    store: audioQueueStore,
    onError: (msg) => setVoiceError(msg),
  });
  const queue = useAudioQueue({
    store: audioQueueStore,
    adapter: og118VoiceAdapter,
    onTranscribed: (_id, text) => {
      if (text) {
        setComposerAppend(text);
      } else {
        // Empty transcript: audio stays in the queue as-is; user can retry or delete.
        setVoiceError('El servidor no reconoció texto. El audio se conserva para revisión.');
      }
    },
    onError: (_id, msg) => {
      console.error('[og118] stt queue', msg);
      setVoiceError(msg);
    },
  });

  // The backend returned 401 (gated cloud, no/invalid token). Surface a usable
  // affordance to paste the access token at runtime (it lives only in this
  // browser's localStorage — never in the bundle, never in conversation storage).
  const needsAuth =
    turn.status === 'error' && (turn.errorMessage ?? '').startsWith(AUTH401);

  const saveToken = () => {
    const t = tokenInput.trim();
    if (!t) return;
    setToken(t);
    agent.reset?.(); // clear the error banner; the user re-sends with the token set
  };

  const authBanner = needsAuth ? (
    <div
      style={{
        marginBottom: '0.75rem',
        padding: '0.75rem',
        borderRadius: 10,
        border: '1px solid rgba(248,113,113,0.35)',
        background: 'rgba(248,113,113,0.08)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
      }}
    >
      <span style={{ color: '#fca5a5', fontSize: '0.85rem' }}>
        Acceso restringido — pega tu token de og118 para continuar.
      </span>
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <input
          type="password"
          value={tokenInput}
          onChange={(e) => setTokenInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') saveToken();
          }}
          placeholder="og118 access token"
          style={{
            flex: 1,
            padding: '0.5rem 0.75rem',
            borderRadius: 8,
            border: '1px solid rgba(255,255,255,0.15)',
            background: 'rgba(15,23,42,0.6)',
            color: '#e2e8f0',
            fontSize: '0.85rem',
          }}
        />
        <button
          onClick={saveToken}
          style={{
            padding: '0.5rem 1rem',
            borderRadius: 8,
            border: '1px solid var(--og-accent, #34d399)',
            background: 'transparent',
            color: 'var(--og-accent, #34d399)',
            fontSize: '0.85rem',
            cursor: 'pointer',
          }}
        >
          Guardar
        </button>
      </div>
    </div>
  ) : null;

  // Voice error banner — covers both recording errors and STT failures.
  // Dismissable inline banner; the message is always a controlled string (no
  // tokens, no PHI, no raw stack traces).
  const voiceErrorBanner = voiceError ? (
    <div
      style={{
        marginBottom: '0.75rem',
        padding: '0.5rem 0.75rem',
        borderRadius: 10,
        border: '1px solid rgba(251,191,36,0.35)',
        background: 'rgba(251,191,36,0.08)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '0.5rem',
      }}
    >
      <span style={{ color: '#fcd34d', fontSize: '0.85rem' }}>{voiceError}</span>
      <button
        onClick={() => setVoiceError(null)}
        aria-label="Descartar error de voz"
        style={{
          border: 'none',
          background: 'transparent',
          color: '#fcd34d',
          fontSize: '1rem',
          cursor: 'pointer',
          lineHeight: 1,
        }}
      >
        ×
      </button>
    </div>
  ) : null;

  // Voice bar (B3-VOICE-OG118-2) — rich TTS playback, a reusable fi-glass
  // primitive (DD-002 / framework-first-canary: og118 consumes, never
  // re-implements). og118 owns only layout/color via CSS.
  const voiceBar = voice.audioUrl ? (
    <div className="og-voice-bar">
      <RichAudioPlayer
        source={{ url: voice.audioUrl }}
        autoPlay
        onEnded={voice.close}
        onError={(e, ctx) => console.error('[og118] tts playback', ctx, e)}
        className="og-voice-player"
        progressClassName="og-voice-progress"
      />
    </div>
  ) : null;

  // B3-VOICE-OG118-6: audio queue panel — shown above the composer when
  // there are pending (non-deleted) artifacts. Privacy notice, item list, and
  // a "clear transcribed" action are all provided by the fi-glass primitive.
  const hasPendingAudios = queue.artifacts.filter((a) => a.state !== 'deleted').length > 0;
  const audioQueuePanel = hasPendingAudios ? (
    <AudioQueuePanel
      queue={queue}
      className="og-audio-queue"
    />
  ) : null;

  // B3-VOICE-OG118-6: durable mic controls for the composer row.
  // Three states — idle, recording, paused — each with the appropriate action
  // buttons. The live equalizer (AudioVisualizer) is embedded here so it sits
  // in the same composer row as the mic button, exactly where the direct-
  // dictation visualizer was (B3-VOICE-FIGLASS-5). og118 tints via CSS only;
  // no internal fi-glass DOM is reached.
  const isActivelyRecording = recording.artifact?.state === 'recording';
  const isPaused = recording.artifact?.state === 'paused';
  const isStopping = recording.artifact?.state === 'stopping';
  const micBtnStyle = {
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '0.375rem',
    borderRadius: 8,
    color: 'var(--og-accent, #34d399)',
  };
  const durableMicSlot = (
    <div className="og-durable-mic" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      {isActivelyRecording && (
        <AudioVisualizer
          levels={recording.bands}
          active
          variant="bars"
          label="Nivel del micrófono"
          className="og-voice-visualizer"
          barClassName="og-voice-bar-bar"
        />
      )}
      {!isActivelyRecording && !isPaused && !isStopping && (
        <ComposerMicSlot
          available={!recording.isAtCapacity}
          recording={false}
          busy={recording.isStarting}
          onStart={() => { void recording.startRecording(); }}
          onStop={() => {}}
          className="og-mic-slot"
        />
      )}
      {isStopping && (
        <span
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            fontSize: '0.75rem',
            color: 'var(--og-accent-muted, #a3a3a3)',
          }}
          aria-live="polite"
          aria-label="Guardando audio"
        >
          <Loader2 size={14} className="animate-spin" style={{ color: '#f59e0b' }} />
          Guardando...
        </span>
      )}
      {isActivelyRecording && (
        <>
          <button
            type="button"
            onClick={recording.pauseRecording}
            aria-label="Pausar grabación"
            className="og-mic-pause"
            style={micBtnStyle}
          >
            <Pause size={18} />
          </button>
          <button
            type="button"
            onClick={() => { void recording.stopRecording().then(() => queue.reload()); }}
            aria-label="Detener y guardar grabación"
            className="og-mic-stop"
            style={micBtnStyle}
          >
            <Square size={18} />
          </button>
        </>
      )}
      {isPaused && (
        <>
          <button
            type="button"
            onClick={recording.resumeRecording}
            aria-label="Reanudar grabación"
            className="og-mic-resume"
            style={micBtnStyle}
          >
            <Play size={18} />
          </button>
          <button
            type="button"
            onClick={() => { void recording.stopRecording().then(() => queue.reload()); }}
            aria-label="Detener y guardar grabación"
            className="og-mic-stop"
            style={micBtnStyle}
          >
            <Square size={18} />
          </button>
        </>
      )}
    </div>
  );

  // Wait for the first hydration so we never send with a null session id nor
  // flash an empty start screen over a stored conversation.
  if (!lib.ready) {
    return <div className="og-loading">Cargando…</div>;
  }

  return (
    <div className="og-shell">
      <Og118Sidebar
        conversations={lib.conversations}
        activeId={lib.activeId}
        onNew={lib.newConversation}
        onSwitch={(id) =>
          void lib.switchConversation(id).catch((e) =>
            console.error('[og118] switch failed', e),
          )
        }
        onDelete={(id) =>
          void lib.deleteConversation(id).catch((e) =>
            console.error('[og118] delete failed', e),
          )
        }
        disabled={conversation.isStreaming}
      />
      <div className="og-chat-main">
        <AgentConversationSurface
          // Route the surface's built-in "new chat" through the library so it
          // mints a fresh id (and thus a fresh session) instead of just clearing
          // the thread — otherwise the next message would clobber the active chat.
          conversation={{ ...conversation, newConversation: lib.newConversation }}
          composerPlaceholder="Pregúntale a og118 (verás su plan en vivo)…"
          newChatLabel="Nuevo chat"
          // The sidebar's "+ Nuevo chat" is the single new-chat CTA (B3-OG118-5);
          // the surface's floating button would duplicate it. The sidebar stays
          // visible on mobile (narrow, not hidden), so no affordance is lost.
          showNewChatButton={false}
          emptyState={<Og118StartScreen />}
          aboveComposer={
            <>
              {authBanner}
              {voiceErrorBanner}
              {voiceBar}
              {audioQueuePanel}
            </>
          }
          composerAreaClassName="og-composer-area glass-chat-composer"
          composerTextareaClassName="glass-chat-composer-input"
          // B3-VOICE-OG118-6: durable mic replaces direct-dictation voiceAdapter.
          // voiceAdapter is NOT passed here (no transcribe capability = no built-in
          // direct-dictation mic). TTS is handled separately via useVoice above.
          // micSlotOverride puts the durable controls in the same composer row slot.
          micSlotOverride={durableMicSlot}
          // B3-VOICE-OG118-6: pull-once transcript injection from the durable queue.
          composerAppend={composerAppend}
          onComposerAppendConsumed={() => setComposerAppend('')}
          // Visible send button (like AURITY), styled with the og emerald accent.
          sendButtonClassName="og-send-btn"
          sendButtonIconClassName="og-send-icon"
          // Per-role bubble tint via the fi-glass resolver slot (FIGLASS-3):
          // user turns get the emerald fill, assistant turns keep the frosted
          // glass card. Both classes ship in the glass-chat preset and the
          // resolver also drives the live streaming assistant bubble.
          messageBubbleClassName={(m) =>
            m.role === 'user'
              ? 'glass-chat-bubble-user'
              : 'glass-chat-bubble-assistant'
          }
          // Copy stays on every message; Speak is added on assistant messages
          // only. renderActions overrides the default showCopyAction.
          renderActions={(m) => (
            <Og118MessageActions
              message={m}
              currentVoice={voice.currentVoice}
              onSpeak={voice.generateAudio}
              ttsLoading={voice.isLoading}
              ttsActiveText={voice.currentText}
              ttsHasCached={voice.hasCachedAudio}
            />
          )}
        />
      </div>
    </div>
  );
}
