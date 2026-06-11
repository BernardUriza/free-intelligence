// @vitest-environment jsdom
/**
 * Tests for useVoice single-flight + object-URL hygiene (B3-VOICE-FIGLASS-6).
 *
 * The daily-driver audit caught the cost bug: TTS takes seconds, the button gave
 * no feedback, and every spam click fired another PAID synthesize request. The
 * hook now latches in-flight synchronously — N rapid calls collapse to ONE
 * provider request — and revokes the previous clip's object URL on re-generate.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { act, render, cleanup } from '@testing-library/react';
import type { VoiceAdapter } from '@free-intelligence/core';
import { useVoice, type UseVoiceReturn } from './useVoice';

function mountVoice(adapter: VoiceAdapter) {
  const ref: { current: UseVoiceReturn | null } = { current: null };
  function Harness() {
    ref.current = useVoice(adapter);
    return null;
  }
  render(<Harness />);
  return ref;
}

const makeAdapter = () => {
  let release: (b: Blob) => void = () => {};
  const synthesize = vi.fn(
    () => new Promise<Blob>((res) => { release = res; }),
  );
  const adapter: VoiceAdapter = {
    defaultVoice: 'nova',
    availableVoices: [],
    synthesize,
  };
  return { adapter, synthesize, finish: (b = new Blob()) => release(b) };
};

describe('useVoice single-flight (B3-VOICE-FIGLASS-6)', () => {
  afterEach(cleanup);

  it('collapses spam clicks into ONE paid synthesize call', async () => {
    const { adapter, synthesize, finish } = makeAdapter();
    const voice = mountVoice(adapter);

    await act(async () => {
      // 50 frantic clicks, same message — the audit scenario.
      for (let i = 0; i < 50; i++) void voice.current!.generateAudio('hola', 'nova');
    });
    expect(synthesize).toHaveBeenCalledTimes(1);
    expect(voice.current!.isLoading).toBe(true);

    await act(async () => { finish(); });
    expect(voice.current!.isLoading).toBe(false);
    expect(voice.current!.audioUrl).toMatch(/^blob:/);
  });

  it('allows a new generation after the previous one settles', async () => {
    const { adapter, synthesize, finish } = makeAdapter();
    const voice = mountVoice(adapter);

    await act(async () => { void voice.current!.generateAudio('uno'); });
    await act(async () => { finish(); });
    await act(async () => { void voice.current!.generateAudio('dos'); });

    expect(synthesize).toHaveBeenCalledTimes(2);
    expect(synthesize).toHaveBeenLastCalledWith('dos', 'nova');
  });

  it('releases the latch after a synthesis failure (retry stays possible)', async () => {
    const synthesize = vi.fn().mockRejectedValueOnce(new Error('boom')).mockResolvedValue(new Blob());
    const adapter: VoiceAdapter = { defaultVoice: 'nova', availableVoices: [], synthesize };
    const voice = mountVoice(adapter);

    await act(async () => { await voice.current!.generateAudio('falla'); });
    expect(voice.current!.isLoading).toBe(false);

    await act(async () => { await voice.current!.generateAudio('reintento'); });
    expect(synthesize).toHaveBeenCalledTimes(2);
  });

  it('serves a repeated text+voice from the session cache (no second paid call)', async () => {
    const synthesize = vi.fn(async () => new Blob(['mp3'], { type: 'audio/mpeg' }));
    const adapter: VoiceAdapter = { defaultVoice: 'nova', availableVoices: [], synthesize };
    const voice = mountVoice(adapter);

    await act(async () => { await voice.current!.generateAudio('hola', 'nova'); });
    const firstUrl = voice.current!.audioUrl;
    await act(async () => { await voice.current!.generateAudio('hola', 'nova'); });

    expect(synthesize).toHaveBeenCalledTimes(1); // cache hit: zero provider spend
    expect(voice.current!.audioUrl).toMatch(/^blob:/);
    expect(voice.current!.audioUrl).not.toBe(firstUrl); // fresh URL per playback
  });

  it('different text or different voice each bill a new synthesis', async () => {
    const synthesize = vi.fn(async () => new Blob(['mp3'], { type: 'audio/mpeg' }));
    const adapter: VoiceAdapter = { defaultVoice: 'nova', availableVoices: [], synthesize };
    const voice = mountVoice(adapter);

    await act(async () => { await voice.current!.generateAudio('hola', 'nova'); });
    await act(async () => { await voice.current!.generateAudio('adiós', 'nova'); });
    await act(async () => { await voice.current!.generateAudio('hola', 'ava'); });

    expect(synthesize).toHaveBeenCalledTimes(3);
  });

  it('never caches a failed synthesis: retrying the SAME text calls the provider again', async () => {
    const synthesize = vi
      .fn()
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValue(new Blob(['mp3']));
    const adapter: VoiceAdapter = { defaultVoice: 'nova', availableVoices: [], synthesize };
    const voice = mountVoice(adapter);

    await act(async () => { await voice.current!.generateAudio('mismo texto'); });
    await act(async () => { await voice.current!.generateAudio('mismo texto'); });
    await act(async () => { await voice.current!.generateAudio('mismo texto'); });

    // 1 failure (uncached) + 1 success (cached) + 1 hit = 2 provider calls.
    expect(synthesize).toHaveBeenCalledTimes(2);
  });

  it('never caches an empty blob', async () => {
    const synthesize = vi.fn(async () => new Blob([]));
    const adapter: VoiceAdapter = { defaultVoice: 'nova', availableVoices: [], synthesize };
    const voice = mountVoice(adapter);

    await act(async () => { await voice.current!.generateAudio('vacío'); });
    await act(async () => { await voice.current!.generateAudio('vacío'); });

    expect(synthesize).toHaveBeenCalledTimes(2);
  });

  it('evicts the least-recently-used clip beyond the cache bound', async () => {
    const synthesize = vi.fn(async () => new Blob(['mp3']));
    const adapter: VoiceAdapter = { defaultVoice: 'nova', availableVoices: [], synthesize };
    const voice = mountVoice(adapter);

    // Fill the cache (TTS_CACHE_MAX_CLIPS = 8), then push one more.
    for (let i = 0; i < 9; i++) {
      await act(async () => { await voice.current!.generateAudio(`clip ${i}`); });
    }
    expect(synthesize).toHaveBeenCalledTimes(9);

    // 'clip 0' was evicted → re-billed. 'clip 8' is still cached → free.
    await act(async () => { await voice.current!.generateAudio('clip 8'); });
    expect(synthesize).toHaveBeenCalledTimes(9);
    await act(async () => { await voice.current!.generateAudio('clip 0'); });
    expect(synthesize).toHaveBeenCalledTimes(10);
  });

  it('changeVoice also hits the cache for an already-synthesized voice', async () => {
    const synthesize = vi.fn(async () => new Blob(['mp3']));
    const adapter: VoiceAdapter = { defaultVoice: 'nova', availableVoices: [], synthesize };
    const voice = mountVoice(adapter);

    await act(async () => { await voice.current!.generateAudio('texto', 'nova'); });
    await act(async () => { await voice.current!.changeVoice('ava'); });   // miss → bill
    await act(async () => { await voice.current!.changeVoice('nova'); });  // hit → free

    expect(synthesize).toHaveBeenCalledTimes(2);
  });

  it('hasCachedAudio reports cache state per text+voice (B3-VOICE-FIGLASS-8)', async () => {
    const synthesize = vi.fn(async () => new Blob(['mp3']));
    const adapter: VoiceAdapter = { defaultVoice: 'nova', availableVoices: [], synthesize };
    const voice = mountVoice(adapter);

    expect(voice.current!.hasCachedAudio('hola', 'nova')).toBe(false);
    await act(async () => { await voice.current!.generateAudio('hola', 'nova'); });

    expect(voice.current!.hasCachedAudio('hola', 'nova')).toBe(true);
    expect(voice.current!.hasCachedAudio('hola')).toBe(true); // default voice = nova
    expect(voice.current!.hasCachedAudio('otro texto', 'nova')).toBe(false);
    expect(voice.current!.hasCachedAudio('hola', 'ava')).toBe(false);
  });

  it('hasCachedAudio stays false after a failed synthesis', async () => {
    const synthesize = vi.fn().mockRejectedValue(new Error('boom'));
    const adapter: VoiceAdapter = { defaultVoice: 'nova', availableVoices: [], synthesize };
    const voice = mountVoice(adapter);

    await act(async () => { await voice.current!.generateAudio('falla'); });
    expect(voice.current!.hasCachedAudio('falla')).toBe(false);
  });

  it('revokes the previous blob object URL when re-generating', async () => {
    const revoke = vi.spyOn(URL, 'revokeObjectURL');
    const { adapter, finish } = makeAdapter();
    const voice = mountVoice(adapter);

    await act(async () => { void voice.current!.generateAudio('uno'); });
    await act(async () => { finish(); });
    const firstUrl = voice.current!.audioUrl;

    await act(async () => { void voice.current!.generateAudio('dos'); });
    expect(revoke).toHaveBeenCalledWith(firstUrl);
    revoke.mockRestore();
  });
});
