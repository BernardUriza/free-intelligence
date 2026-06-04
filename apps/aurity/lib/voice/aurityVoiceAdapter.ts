/**
 * aurityVoiceAdapter — aurity's implementation of core's VoiceAdapter.
 *
 * This is aurity's DOMAIN layer: it owns the endpoints, the provider list and
 * the STT session. fi-glass's useVoice/useDictation consume ONLY this object and
 * never see `api`, `ROUTES` or `VOICE_GROUPS`.
 *
 * - synthesize(): same POST {ROUTES.tts}/synthesize -> Blob the former
 *   useAudioPlayer made → TTS behavior preserved, just routed through the adapter.
 * - transcribe(): same chunk upload (ROUTES.stream) + job poll (ROUTES.jobs)
 *   useChatVoiceRecorder does, minus the React metrics state. Needs the userId to
 *   build the `chat_{userId}` session, so it lives behind a factory.
 *
 * Two exports:
 * - `aurityVoiceAdapter`        — TTS-only (no session needed), for ChatMessage.
 * - `makeAurityVoiceAdapter(id)` — TTS + STT, for dictation consumers.
 */

import type {
  VoiceAdapter,
  VoiceOption,
  TranscribeContext,
  TranscriptResult,
} from '@free-intelligence/core';
import { VOICE_GROUPS } from '@aurity-standalone/types/voices';
import { api } from '@/lib/api/client';
import { ROUTES } from '@/lib/api/routes';

const availableVoices: VoiceOption[] = VOICE_GROUPS.flatMap((group) =>
  group.voices.map((v) => ({
    id: v.value,
    label: v.label,
    group: group.label,
  }))
);

async function synthesize(text: string, voice: string = 'nova') {
  // Same call as the former useAudioPlayer.generateAudio — behavior preserved.
  return api.blob(`${ROUTES.tts}/synthesize`, { text, voice, speed: 1.0 });
}

/** TTS-only adapter (no STT session) — used by ChatMessage's speak button. */
export const aurityVoiceAdapter: VoiceAdapter = {
  availableVoices,
  defaultVoice: 'nova',
  synthesize,
};

/**
 * Full adapter (TTS + STT) bound to a user's dictation session. STT mirrors
 * useChatVoiceRecorder's upload+poll against the same endpoints (which the
 * frontend rewrites to /api/workflows/aurity/*).
 */
export function makeAurityVoiceAdapter(userId: string): VoiceAdapter {
  const sessionId = `chat_${userId.replace(/[^a-zA-Z0-9_-]/g, '_')}`;

  return {
    availableVoices,
    defaultVoice: 'nova',
    synthesize,

    async transcribe(
      chunk: Blob,
      ctx?: TranscribeContext
    ): Promise<TranscriptResult> {
      const index = ctx?.index ?? 0;

      const form = new FormData();
      form.append('session_id', sessionId);
      form.append('chunk_number', String(index));
      form.append('mode', 'chat'); // ephemeral chat mode
      form.append('audio', chunk, 'chunk.webm');
      await api.upload(ROUTES.stream, form);

      // Poll the job until the transcript for this chunk lands (or timeout).
      for (let attempt = 0; attempt < 30; attempt++) {
        if (ctx?.signal?.aborted) break;
        const job = await api.get<{
          transcript?: string;
          status?: string;
          error?: string;
        }>(`${ROUTES.jobs}/${sessionId}`);
        if (job.error) break;
        if (job.transcript) return { text: job.transcript };
        if (job.status === 'completed') return { text: job.transcript ?? '' };
        await new Promise((r) => setTimeout(r, 500));
      }
      return { text: '' };
    },
  };
}
