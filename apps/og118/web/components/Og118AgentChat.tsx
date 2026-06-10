'use client';

/**
 * og118 agentic chat — the glass-box surface, now local-first (DD-002B1.3).
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
import { AgentConversationSurface, useAgentConversation } from 'fi-glass/agent';
import {
  IndexedDBConversationLibrary,
  useConversationLibrary,
} from 'fi-glass/conversation';
import {
  useVoice,
  RichAudioPlayer,
  AudioVisualizer,
  ComposerMicSlot,
} from 'fi-glass/voice';
import { useOg118Agent } from '@/lib/useOg118Agent';
import { getToken, setToken, AUTH401 } from '@/lib/og118Token';
import { og118VoiceAdapter } from '@/lib/og118VoiceAdapter';
import { Og118StartScreen } from './Og118StartScreen';
import { Og118Sidebar } from './Og118Sidebar';
import { Og118MessageActions } from './Og118MessageActions';

// Module-level singleton. The constructor is SSR-safe (it stores config only,
// never touches indexedDB), so one stable instance shared across renders and
// remounts is correct and avoids reopening the database.
const conversationLibrary = new IndexedDBConversationLibrary();

// Static rest pattern for the visualizer. B3-VOICE-OG118-2 adopts the fi-glass
// AudioVisualizer as a discoverable affordance, but no live analyser is wired
// here (no STT, no recording, no Web Audio in og118). Rendering at rest
// (active={false}) is honest: the equalizer is present but has no live signal
// yet — it lights up when a real mic/analyser pipeline lands.
const VOICE_REST_LEVELS = [0.3, 0.6, 0.45, 0.75, 0.5, 0.65, 0.4, 0.55];

export function Og118AgentChat() {
  const lib = useConversationLibrary(conversationLibrary);
  const agent = useOg118Agent(lib.activeId);
  const conversation = useAgentConversation(agent, {
    conversationId: lib.activeId,
    initialMessages: lib.activeMessages,
    onMessagesChange: lib.persist,
  });
  const [tokenInput, setTokenInput] = useState(() => getToken() ?? '');
  const { turn } = conversation;

  // TTS consumer wiring (B3-TTS-1): synthesis goes through og118's adapter
  // (backend /tts/synthesize); fi-glass owns playback + object-URL lifecycle.
  // No audio state lives in og118 — useVoice resolves the Blob to a URL and
  // AudioPlayer plays it.
  const voice = useVoice(og118VoiceAdapter, {
    onError: (e, ctx) => console.error('[og118] tts', ctx, e),
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

  // Voice bar (B3-VOICE-OG118-2) — the rich playback + visualizer + mic slot,
  // all reusable fi-glass primitives (DD-002 / framework-first-canary: og118
  // consumes, never re-implements). og118 owns only layout/color via CSS.
  //   • RichAudioPlayer: full transport + scrubber, shown while a TTS clip is
  //     loaded. fi-glass owns the <audio> element and the object-URL lifecycle.
  //   • AudioVisualizer: idle equalizer affordance (no live analyser wired yet).
  //   • ComposerMicSlot: visible but available={false} — the mic is discoverable
  //     yet clearly disabled. No STT adapter, no mic permission, no recording.
  const voiceBar = (
    <div className="og-voice-bar">
      {voice.audioUrl ? (
        <RichAudioPlayer
          source={{ url: voice.audioUrl }}
          autoPlay
          onEnded={voice.close}
          onError={(e, ctx) => console.error('[og118] tts playback', ctx, e)}
          className="og-voice-player"
          progressClassName="og-voice-progress"
        />
      ) : null}
      <AudioVisualizer
        levels={VOICE_REST_LEVELS}
        active={false}
        variant="bars"
        className="og-voice-visualizer"
        barClassName="og-voice-bar-bar"
        label="Nivel de voz (sin señal en vivo todavía)"
      />
      <ComposerMicSlot
        available={false}
        className="og-mic-slot"
        unavailableLabel="Dictado por voz no disponible todavía (STT pendiente)"
      />
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
          emptyState={<Og118StartScreen />}
          aboveComposer={
            <>
              {authBanner}
              {voiceBar}
            </>
          }
          composerAreaClassName="og-composer-area glass-chat-composer"
          composerTextareaClassName="glass-chat-composer-input"
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
            />
          )}
        />
      </div>
    </div>
  );
}
