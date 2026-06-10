import { describe, it, expect, vi } from 'vitest';
import {
  createOg118VoiceAdapter,
  Og118TTSError,
  Og118STTError,
  OG118_VOICES,
  OG118_DEFAULT_VOICE,
} from '../og118VoiceAdapter';

const BASE = 'https://tts.example.test';
const AUTH = () => ({ Authorization: 'Bearer test-token' });

/** Build an adapter with a stubbed fetch (no network, no DOM). */
function adapterWith(fetchImpl: typeof fetch) {
  return createOg118VoiceAdapter({ baseUrl: BASE, authHeaders: AUTH, fetchImpl });
}

describe('og118VoiceAdapter.synthesize', () => {
  it('exposes the voice catalogue and default voice', () => {
    const adapter = adapterWith(vi.fn());
    expect(adapter.defaultVoice).toBe(OG118_DEFAULT_VOICE);
    expect(adapter.availableVoices).toEqual(OG118_VOICES);
    expect(adapter.availableVoices?.some((v) => v.id === 'nova')).toBe(true);
  });

  it('POSTs to /tts/synthesize with auth + body and returns the audio Blob', async () => {
    const audio = new Blob([new Uint8Array([1, 2, 3])], { type: 'audio/mpeg' });
    // The backend sets the audio content-type header; Response.blob() derives the
    // blob's type from that header, so the fixture must mirror it.
    const fetchImpl = vi.fn(
      async () => new Response(audio, { status: 200, headers: { 'content-type': 'audio/mpeg' } }),
    );
    const adapter = adapterWith(fetchImpl as unknown as typeof fetch);

    const result = await adapter.synthesize!('hola og118', 'shimmer');

    expect(fetchImpl).toHaveBeenCalledTimes(1);
    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${BASE}/tts/synthesize`);
    expect(init.method).toBe('POST');
    expect((init.headers as Record<string, string>)['Content-Type']).toBe('application/json');
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer test-token');
    expect(JSON.parse(init.body as string)).toEqual({
      text: 'hola og118',
      voice: 'shimmer',
      response_format: 'mp3',
      speed: 1.0,
    });

    expect(result).toBeInstanceOf(Blob);
    expect((result as Blob).type).toBe('audio/mpeg');
  });

  it('defaults the voice to nova when none is given', async () => {
    const fetchImpl = vi.fn(async () => new Response(new Blob([]), { status: 200 }));
    const adapter = adapterWith(fetchImpl as unknown as typeof fetch);
    await adapter.synthesize!('texto');
    const [, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(init.body as string).voice).toBe('nova');
  });

  it('maps 401 to an explicit unauthorized TTS error', async () => {
    const fetchImpl = vi.fn(async () => new Response('Unauthorized', { status: 401 }));
    const adapter = adapterWith(fetchImpl as unknown as typeof fetch);
    await expect(adapter.synthesize!('x')).rejects.toMatchObject({
      name: 'Og118TTSError',
      code: 'TTS_UNAUTHORIZED',
      status: 401,
    });
  });

  it('surfaces the backend code when TTS is not configured (503)', async () => {
    const body = JSON.stringify({
      detail: { code: 'TTS_NOT_CONFIGURED', message: 'TTS is not configured on this deployment.' },
    });
    const fetchImpl = vi.fn(
      async () =>
        new Response(body, { status: 503, headers: { 'content-type': 'application/json' } }),
    );
    const adapter = adapterWith(fetchImpl as unknown as typeof fetch);
    const err = await adapter.synthesize!('x').catch((e) => e);
    expect(err).toBeInstanceOf(Og118TTSError);
    expect(err.code).toBe('TTS_NOT_CONFIGURED');
    expect(err.status).toBe(503);
    expect(err.message).toContain('not configured');
  });

  it('maps a network/transport failure to TTS_NETWORK', async () => {
    const fetchImpl = vi.fn(async () => {
      throw new TypeError('Failed to fetch');
    });
    const adapter = adapterWith(fetchImpl as unknown as typeof fetch);
    const err = await adapter.synthesize!('x').catch((e) => e);
    expect(err).toBeInstanceOf(Og118TTSError);
    expect(err.code).toBe('TTS_NETWORK');
    expect(err.status).toBeNull();
  });
});

describe('og118VoiceAdapter.transcribe', () => {
  const chunk = () => new Blob([new Uint8Array([1, 2, 3, 4])], { type: 'audio/webm' });

  it('POSTs multipart audio to /stt/transcribe with auth and returns the text', async () => {
    const fetchImpl = vi.fn(
      async () =>
        new Response(JSON.stringify({ text: 'hola og118, te escucho' }), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
    );
    const adapter = adapterWith(fetchImpl as unknown as typeof fetch);

    const result = await adapter.transcribe!(chunk(), { index: 0 });

    expect(result).toEqual({ text: 'hola og118, te escucho' });
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${BASE}/stt/transcribe`);
    expect(init.method).toBe('POST');
    // Multipart: the body is FormData and we must NOT set Content-Type (the
    // browser supplies the boundary). The bearer still rides along.
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.headers as Record<string, string>)['Content-Type']).toBeUndefined();
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer test-token');
    expect((init.body as FormData).get('audio')).toBeInstanceOf(Blob);
  });

  it('returns an empty string when the backend transcript is empty', async () => {
    const fetchImpl = vi.fn(
      async () =>
        new Response(JSON.stringify({ text: '' }), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
    );
    const adapter = adapterWith(fetchImpl as unknown as typeof fetch);
    expect(await adapter.transcribe!(chunk(), { index: 1 })).toEqual({ text: '' });
  });

  it('forwards the abort signal from the transcribe context', async () => {
    const controller = new AbortController();
    const fetchImpl = vi.fn(
      async () => new Response(JSON.stringify({ text: 'ok' }), { status: 200 }),
    );
    const adapter = adapterWith(fetchImpl as unknown as typeof fetch);
    await adapter.transcribe!(chunk(), { index: 0, signal: controller.signal });
    const [, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(init.signal).toBe(controller.signal);
  });

  it('surfaces the backend code when STT is not configured (503)', async () => {
    const body = JSON.stringify({
      detail: { code: 'STT_NOT_CONFIGURED', message: 'STT is not configured on this deployment.' },
    });
    const fetchImpl = vi.fn(
      async () =>
        new Response(body, { status: 503, headers: { 'content-type': 'application/json' } }),
    );
    const adapter = adapterWith(fetchImpl as unknown as typeof fetch);
    const err = await adapter.transcribe!(chunk()).catch((e) => e);
    expect(err).toBeInstanceOf(Og118STTError);
    expect(err.code).toBe('STT_NOT_CONFIGURED');
    expect(err.status).toBe(503);
  });

  it('maps 401 to an explicit unauthorized STT error', async () => {
    const fetchImpl = vi.fn(async () => new Response('Unauthorized', { status: 401 }));
    const adapter = adapterWith(fetchImpl as unknown as typeof fetch);
    await expect(adapter.transcribe!(chunk())).rejects.toMatchObject({
      name: 'Og118STTError',
      code: 'STT_UNAUTHORIZED',
      status: 401,
    });
  });

  it('maps a network/transport failure to STT_NETWORK', async () => {
    const fetchImpl = vi.fn(async () => {
      throw new TypeError('Failed to fetch');
    });
    const adapter = adapterWith(fetchImpl as unknown as typeof fetch);
    const err = await adapter.transcribe!(chunk()).catch((e) => e);
    expect(err).toBeInstanceOf(Og118STTError);
    expect(err.code).toBe('STT_NETWORK');
    expect(err.status).toBeNull();
  });

  it('maps a non-JSON 2xx body to an explicit STT_BAD_RESPONSE instead of a SyntaxError', async () => {
    // A 200 whose body is not JSON (e.g. a proxy HTML page) must not bubble up
    // as a bare SyntaxError; it funnels through Og118STTError like every other
    // failure so the UI's onVoiceError path stays uniform.
    const fetchImpl = vi.fn(
      async () =>
        new Response('<html>not json</html>', {
          status: 200,
          headers: { 'content-type': 'text/html' },
        }),
    );
    const adapter = adapterWith(fetchImpl as unknown as typeof fetch);
    const err = await adapter.transcribe!(chunk()).catch((e) => e);
    expect(err).toBeInstanceOf(Og118STTError);
    expect(err.code).toBe('STT_BAD_RESPONSE');
    expect(err.status).toBe(200);
  });
});
