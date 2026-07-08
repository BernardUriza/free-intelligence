'use client';

/**
 * useOg118VoiceComposer — og118's voice/audio render-bundle for the chat composer.
 *
 * Owns the consumer-side wiring of three fi-glass primitives — useVoice (TTS),
 * useDurableRecording (mic + IndexedDB capture) and useAudioQueue (transcription)
 * — plus the local voiceError / composerAppend UI state. It returns the ReactNodes
 * the chat surface slots into distinct props (aboveComposer, micSlotOverride,
 * composerAppend) and the live `voice` handle for per-message Speak actions.
 *
 * DD-002 / framework-first-canary: og118 CONSUMES these primitives, it never
 * re-implements them. This hook is pure consumer glue (transport adapter + layout),
 * not a reusable capability — the durable-audio machinery itself lives in fi-glass.
 */

import { useState, type ReactNode } from 'react';
import { Loader2, Pause, Square } from 'lucide-react';
import {
  useVoice,
  RichAudioPlayer,
  useDurableRecording,
  useAudioQueue,
  AudioQueuePanel,
  AudioDraftPlayer,
  ComposerMicSlot,
  AudioVisualizer,
  type AudioQueueStore,
} from 'fi-glass/voice';
import { og118VoiceAdapter } from './og118VoiceAdapter';

export interface Og118VoiceComposer {
  voiceErrorBanner: string | null;
  setVoiceError: (message: string | null) => void;
  voiceBar: ReactNode;
  audioDraftPlayer: ReactNode;
  audioQueuePanel: ReactNode;
  durableMicSlot: ReactNode;
  composerAppend: string;
  clearComposerAppend: () => void;
  voice: ReturnType<typeof useVoice>;
}

export function useOg118VoiceComposer(audioQueueStore: AudioQueueStore): Og118VoiceComposer {
  // Voice errors (STT recording errors + transcription failures). The adapter only
  // emits controlled error messages (no tokens, no PHI, no stack), so the string
  // is safe to render verbatim in the dismissable banner the consumer renders.
  const [voiceError, setVoiceError] = useState<string | null>(null);
  // Pull-once composer injection: a durable-queue transcription lands here, the
  // surface appends it, then onComposerAppendConsumed resets it to ''.
  const [composerAppend, setComposerAppend] = useState('');

  // TTS (B3-TTS-1): synthesis goes through og118's adapter (/tts/synthesize);
  // fi-glass owns playback + object-URL lifecycle. No audio state lives here.
  const voice = useVoice(og118VoiceAdapter, {
    onError: (e, ctx) => console.error('[og118] tts', ctx, e),
  });

  // B3-VOICE-OG118-6: durable local audio capture. useDurableRecording owns the
  // mic + IndexedDB save; useAudioQueue owns transcription + queue management.
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
        setVoiceError('El servidor no reconoció texto. El audio se conserva para revisión.');
      }
    },
    onError: (_id, msg) => {
      console.error('[og118] stt queue', msg);
      setVoiceError(msg);
    },
  });

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

  // B3-VOICE-FIGLASS-10: two draft modes share the same player slot:
  // 1. PAUSED RECORDING — the active artifact in 'paused' state; segmented pause
  //    (FIGLASS-18) exposes the recorded-so-far WAV as pausedPreviewBlob.
  // 2. SAVED DRAFT — the most recent queue artifact not yet acted on.
  const pausedRecordingArtifact =
    recording.artifact?.state === 'paused' ? recording.artifact : null;

  const draftArtifact = [...queue.artifacts]
    .reverse()
    .find(
      (a) =>
        a.state === 'stopping' ||
        a.state === 'queued' ||
        a.state === 'transcribing' ||
        a.state === 'uploading' ||
        a.state === 'failed',
    );

  const audioDraftPlayer = pausedRecordingArtifact ? (
    <AudioDraftPlayer
      artifact={pausedRecordingArtifact}
      pausedPreview={recording.pausedPreviewBlob}
      onResume={recording.resumeRecording}
      onPrimary={() => { void recording.stopRecording().then(() => queue.reload()); }}
      onDiscard={() => { recording.cancelRecording(); }}
      primaryActionLabel="Guardar"
      variant="row"
      className="og-audio-draft og-audio-draft--paused"
    />
  ) : draftArtifact ? (
    <AudioDraftPlayer
      artifact={draftArtifact}
      onGetPlaybackUrl={queue.getPlaybackUrl}
      onPrimary={queue.transcribeArtifact}
      onRetry={queue.retryTranscription}
      onDiscard={queue.deleteArtifact}
      primaryActionLabel="Transcribir"
      variant="row"
      className="og-audio-draft"
    />
  ) : null;

  const backlogCount = queue.artifacts.filter(
    (a) => a.state !== 'deleted' && a.state !== 'archived' && a.id !== draftArtifact?.id,
  ).length;
  const audioQueuePanel = backlogCount > 0 ? (
    <AudioQueuePanel
      queue={queue}
      excludeIds={draftArtifact ? [draftArtifact.id] : []}
      className="og-audio-queue"
    />
  ) : null;

  // B3-VOICE-OG118-6: durable mic controls for the composer row. The live
  // equalizer (AudioVisualizer) sits in the same row as the mic button, where the
  // direct-dictation visualizer was (FIGLASS-5). og118 tints via CSS only.
  const isActivelyRecording = recording.artifact?.state === 'recording';
  const isPaused = recording.artifact?.state === 'paused';
  const isStopping = recording.artifact?.state === 'stopping';
  const durableMicSlot = (
    <div className="og-durable-mic">
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
        <span className="og-mic-saving" aria-live="polite" aria-label="Guardando audio">
          <Loader2 size={14} className="animate-spin og-mic-saving-spinner" />
          Guardando...
        </span>
      )}
      {isActivelyRecording && (
        <>
          <button
            type="button"
            onClick={recording.pauseRecording}
            aria-label="Pausar grabación"
            className="og-mic-pause og-mic-btn"
            data-ref="og118-mic-pause"
          >
            <Pause size={18} />
          </button>
          <button
            type="button"
            onClick={() => { void recording.stopRecording().then(() => queue.reload()); }}
            aria-label="Detener y guardar grabación"
            className="og-mic-stop og-mic-btn"
            data-ref="og118-mic-stop"
          >
            <Square size={18} />
          </button>
        </>
      )}
      {/* When paused, AudioDraftPlayer (above composer) owns the Resume/Stop
          controls — no duplicate buttons here. */}
    </div>
  );

  return {
    voiceErrorBanner: voiceError,
    setVoiceError,
    voiceBar,
    audioDraftPlayer,
    audioQueuePanel,
    durableMicSlot,
    composerAppend,
    clearComposerAppend: () => setComposerAppend(''),
    voice,
  };
}
