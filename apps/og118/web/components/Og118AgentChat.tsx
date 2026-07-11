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
 * assistant fold, live AgentPanel, AND transcript persistence — lives in the
 * framework (fi-glass `useAgentConversation` + `useConversationLibrary` over a
 * ConversationLibrary adapter: the cloud store when signed in, IndexedDB
 * otherwise — see useOg118ConversationLibrary). DD-002-LESSON: the consumer
 * consumes the primitive; it does not re-implement it.
 *
 * Identity: the conversation library owns the active id, which IS the backend
 * session_id (passed to useOg118Agent). One id ⇒ the local transcript and the
 * server's conversation store key the same thread, so a refresh keeps both the
 * visible transcript (IndexedDB) and intra-deploy model continuity.
 */

import { useCallback, useRef, useState } from 'react';
import { Phone, PhoneOff } from 'lucide-react';
import {
  AgentConversationSurface,
  AgentWorkspaceShell,
  useAgentConversation,
} from 'fi-glass/agent';
import { useConversationLibrary } from 'fi-glass/conversation';
import { useAudioQueueStore, AudioVisualizer } from 'fi-glass/voice';
import { useOg118Agent } from '@/lib/useOg118Agent';
import { getToken, setToken, AUTH401 } from '@/lib/og118Token';
import { useOg118Identity } from '@/lib/og118Identity';
import { isAuth0Mode } from '@/lib/authMode';
import { useOg118VoiceComposer } from '@/lib/useOg118VoiceComposer';
import { useOg118ResonanceCall } from '@/lib/useOg118ResonanceCall';
import { Og118StartScreen } from './Og118StartScreen';
import { Og118Sidebar } from './Og118Sidebar';
import { Og118ProjectsSection } from './projects';
import { Og118ElementSelector, Og118ActiveElementStrip } from './Og118ElementSelector';
import { useOg118ConversationLibrary } from '@/lib/useOg118ConversationLibrary';
import { useOg118Projects } from '@/lib/useOg118Projects';
import { useOg118Elements } from '@/lib/useOg118Elements';
import { useOg118ProjectUpload } from '@/lib/useOg118ProjectUpload';
import { Og118MessageActions } from './Og118MessageActions';
import { OG118_AUTHOR, Og118ModelBadge } from './Og118MessageMeta';
import { Og118AuthBanner } from './Og118AuthBanner';
import { Og118VoiceErrorBanner } from './Og118VoiceErrorBanner';

// RESONANCE_CALL_LOOP feature flag: ?resonance=1 query param or localStorage.
// Off by default so the one-shot composer stays the only voice path until opted in.
function readResonanceFlag(): boolean {
  if (typeof window === 'undefined') return false;
  const p = new URLSearchParams(window.location.search);
  if (p.get('resonance') === '1' || p.get('RESONANCE_CALL_LOOP') === '1') return true;
  return window.localStorage.getItem('RESONANCE_CALL_LOOP') === '1';
}

// Per-state copy + whether the equalizer shows live mic input. Live in
// listening/speaking/silence_hold (mic open); dimmed while we process so Bernard
// never mistakes "processing" for "still hearing you".
//
// `idle` carries NO copy: the state line renders only during a call, and the
// call button already says "Llamar". Mapping idle to the button's own label is
// what printed "Llamar (Resonance)  LLAMAR (RESONANCE)" side by side.
const RESONANCE_LABEL: Record<string, string> = {
  listening: 'Escuchando…',
  transcribing: 'Transcribiendo…',
  thinking: 'Pensando…',
  speaking: 'Hablando — puedes interrumpir',
  interrupted: 'Te oigo — interrumpiendo',
  silence_hold: 'Sigo aquí',
  sleep_decay: 'Bajando volumen…',
  ended: 'Llamada finalizada',
};
function resonanceVisualizerActive(state: string): boolean {
  return state === 'listening' || state === 'speaking' || state === 'silence_hold';
}

export function Og118AgentChat() {
  // Identity-scoped local-first stores: each signed-in account gets its OWN
  // IndexedDB database + localStorage keyspace, so two accounts on the same
  // browser never see each other's conversations, audio drafts, or projects
  // (the shared-device leak fix). The hooks memoize per identity; a null userId
  // (bearer / legacy single-tenant) keeps the original shared store.
  const { userId, tokenReady } = useOg118Identity();
  // CONV-CLOUD-1: signed-in ⇒ the server conversation store is authoritative
  // (after a one-time local→cloud migration); unauthenticated/bearer stays on
  // the identity-scoped IndexedDB exactly as before.
  const { library: conversationLibrary, cloud: conversationsCloud } =
    useOg118ConversationLibrary(userId, tokenReady);
  const audioQueueStore = useAudioQueueStore(userId);
  const lib = useConversationLibrary(conversationLibrary);
  const projects = useOg118Projects(userId, tokenReady);
  const elements = useOg118Elements(userId);
  const upload = useOg118ProjectUpload();
  const agent = useOg118Agent(lib.activeId, projects.activeProjectId, elements.selected);
  const conversation = useAgentConversation(agent, {
    // WHO answers when no element is selected. A selected element (Yodo,
    // Oxígeno) overrides it per turn — the backend announces the speaker and
    // fi-glass stamps it onto the message, so the bubble names the real author.
    author: OG118_AUTHOR,
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
  // OG118-IMAGE-UPLOAD-1: a rejected attachment (wrong type / too big) surfaces
  // here — same dismissable-banner pattern as voice errors, controlled string only.
  const [attachError, setAttachError] = useState<string | null>(null);
  const { turn } = conversation;
  const activeElement = elements.elements.find((e) => e.slug === elements.selected);

  // All voice/audio wiring (TTS playback, durable mic, transcription queue) lives
  // in one consumer hook; it returns the render slots the surface distributes.
  const composer = useOg118VoiceComposer(audioQueueStore);

  // RESONANCE: hands-free continuous voice call, behind the RESONANCE_CALL_LOOP
  // flag (off by default — the one-shot composer above stays the fallback). A
  // turn-text ref lets requestAssistantTurn resolve with the streamed answer.
  const [resonanceEnabled] = useState(readResonanceFlag);
  // Resonance speaks the SAME turn the transcript persists: sendAndAwait is the
  // single writer of the user + assistant capsules and resolves with the text to
  // speak. No raw agent.send, no transcript bypass (the capsule-less bug).
  const requestAssistantTurn = useCallback(
    (userText: string) => conversation.sendAndAwait(userText),
    [conversation],
  );
  const resonance = useOg118ResonanceCall({
    enabled: resonanceEnabled,
    appendUserMessage: () => {}, // sendAndAwait owns the user capsule — keep this a no-op
    requestAssistantTurn,
    debug: resonanceEnabled,
  });

  // The backend returned 401 (gated cloud, no/invalid token). Surface a usable
  // affordance to paste the access token at runtime (it lives only in this
  // browser's localStorage — never in the bundle, never in conversation storage).
  // In auth0 mode the AuthGate owns login; the legacy paste-token banner only
  // shows in bearer mode (a 401 there means no/invalid pasted token).
  const needsAuth =
    !isAuth0Mode && turn.status === 'error' && (turn.errorMessage ?? '').startsWith(AUTH401);

  const saveToken = () => {
    const t = tokenInput.trim();
    if (!t) return;
    setToken(t);
    agent.reset?.(); // clear the error banner; the user re-sends with the token set
  };

  const authBanner = needsAuth ? (
    <Og118AuthBanner token={tokenInput} onTokenChange={setTokenInput} onSave={saveToken} />
  ) : null;

  // Voice error banner — covers both recording errors and STT failures. The
  // message is always a controlled string (no tokens, no PHI, no raw stack).
  const voiceErrorBanner = composer.voiceErrorBanner ? (
    <Og118VoiceErrorBanner
      message={composer.voiceErrorBanner}
      onDismiss={() => composer.setVoiceError(null)}
    />
  ) : null;

  // Attachment rejections reuse the same banner presentation (message + dismiss).
  const attachErrorBanner = attachError ? (
    <Og118VoiceErrorBanner message={attachError} onDismiss={() => setAttachError(null)} />
  ) : null;

  // Wait for the first hydration so we never send with a null session id nor
  // flash an empty start screen over a stored conversation.
  if (!lib.ready) {
    return <div className="og-loading">Cargando…</div>;
  }

  return (
    <AgentWorkspaceShell
      responsive
      toggleLabel="Conversaciones"
      sidebar={(shell) => (
        <>
        <Og118ActiveElementStrip element={activeElement} />
        <Og118ProjectsSection
          projects={projects.projects}
          activeProjectId={projects.activeProjectId}
          onCreate={(name) => {
            projects.createProject(name).catch((e) => console.error('create project failed', e));
            shell.close();
          }}
          onSelect={(id) => {
            projects.selectProject(id);
            shell.close();
          }}
          onDelete={(id) =>
            void projects.deleteProject(id).catch((e) =>
              console.error('[og118] delete project failed', e),
            )
          }
          disabled={conversation.isStreaming}
          uploadFile={upload.file}
          uploadStatus={upload.status}
          uploadProgress={upload.progress}
          uploadError={upload.error}
          uploadChunks={upload.result?.chunks ?? null}
          onUpload={(id) => upload.openFilePicker(id)}
          onCancelUpload={upload.cancel}
        />
        <Og118Sidebar
          conversations={lib.conversations}
          activeId={lib.activeId}
          cloud={conversationsCloud}
          onNew={() => {
            lib.newConversation();
            shell.close();
          }}
          onSwitch={(id) => {
            void lib.switchConversation(id).catch((e) =>
              console.error('[og118] switch failed', e),
            );
            shell.close();
          }}
          onDelete={(id) =>
            void lib.deleteConversation(id).catch((e) =>
              console.error('[og118] delete failed', e),
            )
          }
          onRename={(id, title) =>
            void lib.renameConversation(id, title).catch((e) =>
              console.error('[og118] rename failed', e),
            )
          }
          disabled={conversation.isStreaming}
        />
        </>
      )}
      conversation={
        <AgentConversationSurface
          // Route the surface's built-in "new chat" through the library so it
          // mints a fresh id (and thus a fresh session) instead of just clearing
          // the thread — otherwise the next message would clobber the active chat.
          conversation={{ ...conversation, newConversation: lib.newConversation }}
          composerPlaceholder="Pregúntale a og118 (verás su plan en vivo)…"
          newChatLabel="Nuevo chat"
          // The sidebar's "+ Nuevo chat" is the single new-chat CTA (B3-OG118-5);
          // the surface's floating button would duplicate it. On mobile the
          // sidebar lives in the AgentWorkspaceShell drawer (reachable via the
          // hamburger), so the CTA is one tap away — no affordance is lost.
          showNewChatButton={false}
          emptyState={<Og118StartScreen />}
          // Only what must INTERRUPT stays outside the box: system banners and
          // the audio queue. Everything the user SETS before composing moved
          // into the composer's footer rail (COMPOSER-FOOTER-ZONES-1).
          aboveComposer={
            <>
              {authBanner}
              {voiceErrorBanner}
              {attachErrorBanner}
              {composer.voiceBar}
              {composer.audioQueuePanel}
            </>
          }
          // OG118-IMAGE-UPLOAD-1 (ChatGPT parity): the framework owns the whole
          // capability — attach button, paste-an-image, chips, encoding, send.
          // og118 only flips the switch and surfaces rejections in its banner.
          imageAttachments
          onImageAttachmentError={setAttachError}
          // The footer's left rail: element selector + the Resonance call
          // control. A call is a MODE, not a banner — idle it costs one icon,
          // and its live state rises into the composer header below.
          composerFooterStart={
            <>
              <div className="og-element-switch" data-ref="og118-element-switch">
                <Og118ElementSelector
                  elements={elements.elements}
                  selected={elements.selected}
                  onSelect={elements.select}
                  loading={elements.loading}
                />
              </div>
              {resonanceEnabled && (
                <button
                  type="button"
                  className={`og-resonance-call-btn${resonance.isActive ? ' og-resonance-call-btn-active' : ''}`}
                  data-ref="og118-resonance-call"
                  aria-pressed={resonance.isActive}
                  aria-label={resonance.isActive ? 'Colgar la llamada' : 'Llamar por voz (Resonance)'}
                  onClick={() => (resonance.isActive ? resonance.endCall() : void resonance.startCall())}
                >
                  {resonance.isActive ? <PhoneOff aria-hidden /> : <Phone aria-hidden />}
                  <span className="og-resonance-call-label">
                    {resonance.isActive ? 'Colgar' : 'Llamar'}
                  </span>
                </button>
              )}
            </>
          }
          composerFooterStartClassName="og-composer-rail"
          // The frosted preset goes on the BOX (textarea + controls row inside
          // one floating container, AURITY anatomy); og118 owns only spacing.
          composerBoxClassName="og-composer-box glass-chat-composer"
          // COMPOSER-FRAME-2: the recorded-audio draft lives INSIDE the box
          // (ComposerFrame header slot), WhatsApp/Claude review pattern — the
          // transcript lands in the textarea right below it. An active call
          // surfaces its equalizer + state here too: the composer BECOMES the
          // call surface instead of a card floating above it. The ternary keeps
          // an empty fragment from mounting a ghost header row.
          composerHeader={
            resonance.isActive || composer.audioDraftPlayer ? (
              <>
                {resonance.isActive && (
                  <div className="og-resonance-live" data-ref="og118-resonance-bar">
                    <AudioVisualizer
                      levels={resonance.bands}
                      active={resonanceVisualizerActive(resonance.state)}
                      variant="bars"
                      label="Nivel de tu voz"
                      className="og-resonance-visualizer"
                      barClassName="og-voice-bar-bar"
                    />
                    <span className="og-resonance-state" data-ref="og118-resonance-state">
                      {resonance.isHearingUser
                        ? 'Te oigo'
                        : (RESONANCE_LABEL[resonance.state] ?? resonance.state)}
                    </span>
                  </div>
                )}
                {composer.audioDraftPlayer}
              </>
            ) : null
          }
          composerHeaderClassName="og-composer-draft-row"
          composerAreaClassName="og-composer-area"
          composerTextareaClassName="glass-chat-composer-input"
          composerControlsClassName="og-composer-controls"
          // B3-VOICE-OG118-6: durable mic replaces direct-dictation voiceAdapter.
          // voiceAdapter is NOT passed here (no transcribe capability = no built-in
          // direct-dictation mic). TTS is handled separately via useVoice above.
          // micSlotOverride puts the durable controls in the same composer row slot.
          micSlotOverride={composer.durableMicSlot}
          // B3-VOICE-OG118-6: pull-once transcript injection from the durable queue.
          composerAppend={composer.composerAppend}
          onComposerAppendConsumed={composer.clearComposerAppend}
          // Visible send button (like AURITY), styled with the og emerald accent.
          sendButtonClassName="og-send-btn"
          sendButtonIconClassName="og-send-icon"
          // While streaming the send button becomes a live stop control; the
          // danger tint says "this cancels" rather than "this is loading".
          stopButtonClassName="og-stop-btn"
          stopLabel="Detener la respuesta"
          // Per-role bubble tint via the fi-glass resolver slot (FIGLASS-3):
          // user turns get the emerald fill, assistant turns keep the frosted
          // glass card. Both classes ship in the glass-chat preset and the
          // resolver also drives the live streaming assistant bubble.
          messageBubbleClassName={(m) =>
            m.role === 'user'
              ? 'glass-chat-bubble-user'
              : 'glass-chat-bubble-assistant'
          }
          // Header (avatar + author + time) and model badge fill the
          // MessageBubble slots that were sitting empty — app-specific
          // identity/branding, so the wiring lives here, not in fi-glass.
          renderBadge={(m) => <Og118ModelBadge message={m} />}
          // The glass-box is the product's differentiator, and it was rendering
          // as bare text: AgentPanel defaults `classNames.card` to '', so the
          // plan drew with background rgba(0,0,0,0), border 0, padding 0 —
          // indistinguishable from the answer beneath it.
          agentPanelProps={{
            classNames: { card: 'og-agent-card', hint: 'og-agent-hint' },
          }}
          // Copy stays on every message; Speak is added on assistant messages
          // only. renderActions overrides the default showCopyAction.
          renderActions={(m) => (
            <Og118MessageActions
              message={m}
              currentVoice={composer.voice.currentVoice}
              onSpeak={composer.voice.generateAudio}
              ttsLoading={composer.voice.isLoading}
              ttsActiveText={composer.voice.currentText}
              ttsHasCached={composer.voice.hasCachedAudio}
            />
          )}
        />
      }
    />
  );
}
