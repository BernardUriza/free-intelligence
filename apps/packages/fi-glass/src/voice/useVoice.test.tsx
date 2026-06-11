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
