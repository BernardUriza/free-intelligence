/**
 * og118VoiceAdapter — the CONSUMER half of voice (TTS + STT).
 *
 * og118 owns only the I/O. For TTS (B3-TTS-1) it calls `/tts/synthesize`
 * (B3-VOICE-BACKEND-1) and hands the audio Blob back to fi-glass, which owns
 * playback + object-URL lifecycle. For STT (B3-VOICE-OG118-4) it calls
 * `/stt/transcribe` (B3-VOICE-BACKEND-2) and returns the recognized text;
 * fi-glass's AgentConversationSurface (B3-VOICE-FIGLASS-4) owns the recorder,
 * the mic slot and feeding the transcript into the composer. This file therefore
 * touches NO audio elements, object URLs, MediaRecorder or composer state — that
 * would duplicate the framework. It implements exactly two adapter capabilities:
 * `synthesize` and `transcribe`.
 *
 * Auth/transport reuse: the bearer is read through og118's existing `authHeaders()`
 * (localStorage token), identical to how `/chat/stream` authenticates. No new auth
 * path, no token printed or extracted.
 *
 * Testability: a factory (createOg118VoiceAdapter) injects baseUrl/authHeaders/fetch
 * so tests drive it with a fake fetch and never touch the network or the DOM —
 * mirroring the backend's provider dependency seams.
 */

import type {
  VoiceAdapter,
  VoiceOption,
  AudioSource,
  TranscribeContext,
  TranscriptResult,
} from '@free-intelligence/core';
import { authHeaders as defaultAuthHeaders } from './og118Token';

/** Same base URL as the chat transport (useOg118Agent). */
const API = process.env.NEXT_PUBLIC_OG118_API ?? 'http://localhost:8118';

/** Voices the backend (OpenAI-compatible deployment) accepts. */
export const OG118_VOICES: VoiceOption[] = [
  { id: 'nova', label: 'Nova', group: 'OpenAI' },
  { id: 'shimmer', label: 'Shimmer', group: 'OpenAI' },
  { id: 'alloy', label: 'Alloy', group: 'OpenAI' },
  { id: 'echo', label: 'Echo', group: 'OpenAI' },
  { id: 'fable', label: 'Fable', group: 'OpenAI' },
  { id: 'onyx', label: 'Onyx', group: 'OpenAI' },
];

export const OG118_DEFAULT_VOICE = 'nova';

/**
 * Explicit TTS error — every non-OK response and every network failure becomes
 * one of these so the UI (useVoice.onError) can react without parsing raw fetch
 * rejections. `code` prefers the backend's structured code (e.g.
 * TTS_NOT_CONFIGURED) and otherwise derives one from the HTTP status.
 */
export class Og118TTSError extends Error {
  readonly code: string;
  readonly status: number | null;

  constructor(message: string, code: string, status: number | null, options?: { cause?: unknown }) {
    super(message, options);
    this.name = 'Og118TTSError';
    this.code = code;
    this.status = status;
  }
}

/** Map an HTTP status to a fallback code + human message when the body has none. */
function fallbackForStatus(status: number): { code: string; message: string } {
  switch (status) {
    case 400:
      return { code: 'TTS_INVALID_REQUEST', message: 'Texto inválido para síntesis de voz.' };
    case 401:
      return { code: 'TTS_UNAUTHORIZED', message: 'Token de acceso inválido o ausente para TTS.' };
    case 403:
      return { code: 'TTS_FORBIDDEN', message: 'Acceso a TTS denegado.' };
    case 404:
      return { code: 'TTS_NOT_FOUND', message: 'El endpoint de TTS no está disponible.' };
    case 502:
      return { code: 'TTS_UPSTREAM_ERROR', message: 'El proveedor de voz falló.' };
    case 503:
      return { code: 'TTS_NOT_CONFIGURED', message: 'TTS no está configurado en este despliegue.' };
    default:
      return { code: 'TTS_ERROR', message: `Síntesis de voz falló (HTTP ${status}).` };
  }
}

/**
 * Explicit STT error — the dictation twin of {@link Og118TTSError}. Every
 * non-OK response and every network failure becomes one of these so the UI
 * (AgentConversationSurface.onVoiceError) can react without parsing raw fetch
 * rejections.
 */
export class Og118STTError extends Error {
  readonly code: string;
  readonly status: number | null;

  constructor(message: string, code: string, status: number | null, options?: { cause?: unknown }) {
    super(message, options);
    this.name = 'Og118STTError';
    this.code = code;
    this.status = status;
  }
}

/** STT twin of fallbackForStatus: codes/messages for the /stt/transcribe surface. */
function fallbackForStatusStt(status: number): { code: string; message: string } {
  switch (status) {
    case 400:
      return { code: 'STT_INVALID_REQUEST', message: 'Audio inválido para transcripción.' };
    case 401:
      return { code: 'STT_UNAUTHORIZED', message: 'Token de acceso inválido o ausente para STT.' };
    case 403:
      return { code: 'STT_FORBIDDEN', message: 'Acceso a STT denegado.' };
    case 404:
      return { code: 'STT_NOT_FOUND', message: 'El endpoint de transcripción no está disponible.' };
    case 502:
      return { code: 'STT_UPSTREAM_ERROR', message: 'El proveedor de transcripción falló.' };
    case 503:
      return { code: 'STT_NOT_CONFIGURED', message: 'STT no está configurado en este despliegue.' };
    default:
      return { code: 'STT_ERROR', message: `Transcripción falló (HTTP ${status}).` };
  }
}

/** Best-effort extraction of the backend's `{ detail: { code, message } }` body. */
async function readBackendError(res: Response): Promise<{ code?: string; message?: string }> {
  try {
    const body = (await res.json()) as { detail?: { code?: string; message?: string } | string };
    const detail = body?.detail;
    if (detail && typeof detail === 'object') {
      return { code: detail.code, message: detail.message };
    }
    if (typeof detail === 'string') return { message: detail };
  } catch {
    /* non-JSON body (e.g. plain 401) — fall back to status mapping */
  }
  return {};
}

export interface Og118VoiceAdapterDeps {
  /** Backend base URL. Default: NEXT_PUBLIC_OG118_API. */
  baseUrl?: string;
  /** Auth header provider. Default: og118Token.authHeaders (localStorage bearer). */
  authHeaders?: () => Record<string, string>;
  /** Fetch implementation. Default: global fetch. Injected in tests. */
  fetchImpl?: typeof fetch;
}

/**
 * Build an og118 VoiceAdapter. Defaults wire the real backend + auth; tests pass
 * fakes. Implements both `synthesize` (TTS) and `transcribe` (STT) — fi-glass
 * lights up the SpeakButton and the in-composer dictation mic respectively, off
 * the presence of each capability.
 */
export function createOg118VoiceAdapter(deps: Og118VoiceAdapterDeps = {}): VoiceAdapter {
  const baseUrl = deps.baseUrl ?? API;
  const getAuthHeaders = deps.authHeaders ?? defaultAuthHeaders;
  // Bind so the default global fetch keeps its correct `this` (avoids "Illegal
  // invocation" in browsers when destructured).
  const doFetch: typeof fetch = deps.fetchImpl ?? ((input, init) => fetch(input, init));

  return {
    defaultVoice: OG118_DEFAULT_VOICE,
    availableVoices: OG118_VOICES,

    async synthesize(text: string, voice: string = OG118_DEFAULT_VOICE): Promise<AudioSource> {
      let res: Response;
      try {
        res = await doFetch(`${baseUrl}/tts/synthesize`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
          body: JSON.stringify({ text, voice, response_format: 'mp3', speed: 1.0 }),
        });
      } catch (err) {
        throw new Og118TTSError('No se pudo contactar el servicio de voz.', 'TTS_NETWORK', null, {
          cause: err,
        });
      }

      if (!res.ok) {
        const fallback = fallbackForStatus(res.status);
        const backend = await readBackendError(res);
        throw new Og118TTSError(
          backend.message ?? fallback.message,
          backend.code ?? fallback.code,
          res.status,
        );
      }

      // Success → raw audio bytes. Returning a Blob lets fi-glass own the object
      // URL (it revokes only the URLs it creates). We never persist it.
      return res.blob();
    },

    async transcribe(chunk: Blob, ctx?: TranscribeContext): Promise<TranscriptResult> {
      // Multipart upload — the browser sets the multipart boundary, so we must
      // NOT send a Content-Type header (that would override the boundary). The
      // bearer rides along via the same authHeaders() as every other call.
      const form = new FormData();
      // Use the blob's actual MIME type to derive the filename extension so
      // the multipart Content-Disposition matches the real format. useDurableRecording
      // saves audio/wav; direct-dictation used webm — the backend reads the
      // Content-Type of the part, not the extension, but a coherent name avoids
      // ambiguity if the backend logs or inspects filenames.
      const ext = chunk.type === 'audio/wav' ? 'wav' : 'webm';
      form.append('audio', chunk, `chunk.${ext}`);

      let res: Response;
      try {
        res = await doFetch(`${baseUrl}/stt/transcribe`, {
          method: 'POST',
          headers: { ...getAuthHeaders() },
          body: form,
          signal: ctx?.signal,
        });
      } catch (err) {
        throw new Og118STTError(
          'No se pudo contactar el servicio de transcripción.',
          'STT_NETWORK',
          null,
          { cause: err },
        );
      }

      if (!res.ok) {
        const fallback = fallbackForStatusStt(res.status);
        const backend = await readBackendError(res);
        throw new Og118STTError(
          backend.message ?? fallback.message,
          backend.code ?? fallback.code,
          res.status,
        );
      }

      // A 2xx with a non-JSON body would otherwise throw a bare SyntaxError;
      // funnel it through the same explicit-error path as a network failure so
      // the UI always sees an Og118STTError, never a raw parse rejection.
      let data: { text?: string };
      try {
        data = (await res.json()) as { text?: string };
      } catch (err) {
        throw new Og118STTError(
          'El servicio de transcripción devolvió una respuesta inválida.',
          'STT_BAD_RESPONSE',
          res.status,
          { cause: err },
        );
      }
      return { text: data.text ?? '' };
    },
  };
}

/** App singleton wired to the real backend + auth. */
export const og118VoiceAdapter = createOg118VoiceAdapter();
