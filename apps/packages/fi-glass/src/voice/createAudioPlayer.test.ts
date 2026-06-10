/**
 * Unit tests for the headless TTS playback engine (audioPlayer.ts).
 *
 * The engine is dependency-injected precisely so this can run in node with no
 * DOM, no Azure, no network: a FakeAudioElement drives the media events
 * synchronously and counter-based URL helpers prove the object-URL ownership
 * rule (the leak the old useVoice.close left behind). These branches — error,
 * ended, stop/dispose cleanup, external-url-not-revoked — never run reliably in
 * a normal e2e turn, so they get deterministic unit coverage.
 */

import { describe, it, expect, vi } from 'vitest';
import {
  createAudioPlayer,
  clampSeekTarget,
  type AudioElementLike,
} from './createAudioPlayer';

class FakeAudioElement implements AudioElementLike {
  src = '';
  currentTime = 0;
  duration = 0;
  paused = true;
  playShouldReject: unknown = null;
  loadCalls = 0;

  private listeners = new Map<string, Set<() => void>>();

  async play(): Promise<void> {
    if (this.playShouldReject) throw this.playShouldReject;
    this.paused = false;
  }
  pause(): void {
    this.paused = true;
  }
  load(): void {
    this.loadCalls += 1;
  }
  addEventListener(type: string, listener: () => void): void {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type)!.add(listener);
  }
  removeEventListener(type: string, listener: () => void): void {
    this.listeners.get(type)?.delete(listener);
  }
  /** Test helper: fire a media event. */
  emit(type: string): void {
    for (const l of this.listeners.get(type) ?? []) l();
  }
  listenerCount(type: string): number {
    return this.listeners.get(type)?.size ?? 0;
  }
}

function harness(overrides: Partial<Parameters<typeof createAudioPlayer>[0]> = {}) {
  const el = new FakeAudioElement();
  const revoked: string[] = [];
  let n = 0;
  const player = createAudioPlayer({
    createElement: () => el,
    createObjectURL: () => `blob:fake-${++n}`,
    revokeObjectURL: (url) => revoked.push(url),
    ...overrides,
  });
  return { el, revoked, player };
}

const fakeBlob = (): Blob => new Blob(['audio'], { type: 'audio/mpeg' });

describe('createAudioPlayer', () => {
  it('starts idle', () => {
    const { player } = harness();
    expect(player.getState()).toMatchObject({
      status: 'idle',
      isPlaying: false,
      isLoading: false,
      currentSrc: null,
    });
  });

  it('load(Blob) object-URLs the source and enters loading', () => {
    const { el, player } = harness();
    player.load(fakeBlob());
    expect(el.src).toBe('blob:fake-1');
    expect(el.loadCalls).toBe(1);
    expect(player.getState()).toMatchObject({
      status: 'loading',
      isLoading: true,
      currentSrc: 'blob:fake-1',
    });
  });

  it('loadedmetadata clears loading and records duration', () => {
    const { el, player } = harness();
    player.load(fakeBlob());
    el.duration = 12.5;
    el.emit('loadedmetadata');
    expect(player.getState()).toMatchObject({ isLoading: false, duration: 12.5 });
  });

  it('play() marks playing; pause() marks paused', async () => {
    const { player } = harness();
    player.load(fakeBlob());
    await player.play();
    expect(player.getState()).toMatchObject({ status: 'playing', isPlaying: true });
    player.pause();
    expect(player.getState()).toMatchObject({ status: 'paused', isPlaying: false });
  });

  it('ended resets to idle and fires onEnded', () => {
    const onEnded = vi.fn();
    const { el, player } = harness({ onEnded });
    player.load(fakeBlob());
    el.currentTime = 9;
    el.emit('ended');
    expect(onEnded).toHaveBeenCalledOnce();
    expect(player.getState()).toMatchObject({
      status: 'idle',
      isPlaying: false,
      currentTime: 0,
    });
  });

  it('element error sets error state and calls onError', () => {
    const onError = vi.fn();
    const { el, player } = harness({ onError });
    player.load(fakeBlob());
    el.emit('error');
    expect(onError).toHaveBeenCalledOnce();
    expect(player.getState()).toMatchObject({ status: 'error' });
    expect(player.getState().error).toBeInstanceOf(Error);
  });

  it('play() rejection surfaces as error (autoplay-block shape)', async () => {
    const onError = vi.fn();
    const { el, player } = harness({ onError });
    el.playShouldReject = new DOMException('blocked', 'NotAllowedError');
    player.load(fakeBlob());
    await player.play();
    expect(player.getState()).toMatchObject({ status: 'error', isPlaying: false });
    expect(onError).toHaveBeenCalledOnce();
  });

  it('stop() revokes the owned object URL and resets', () => {
    const { player, revoked } = harness();
    player.load(fakeBlob());
    player.stop();
    expect(revoked).toEqual(['blob:fake-1']);
    expect(player.getState()).toMatchObject({
      status: 'idle',
      currentSrc: null,
      currentTime: 0,
    });
  });

  it('loading a new source revokes the previous owned URL (no leak)', () => {
    const { player, revoked } = harness();
    player.load(fakeBlob());
    player.load(fakeBlob());
    expect(revoked).toEqual(['blob:fake-1']);
    expect(player.getState().currentSrc).toBe('blob:fake-2');
  });

  it('a { url } source is used as-is and never revoked (caller owns it)', () => {
    const { el, player, revoked } = harness();
    player.load({ url: 'https://cdn/clip.mp3' });
    expect(el.src).toBe('https://cdn/clip.mp3');
    player.stop();
    expect(revoked).toEqual([]); // external URL must NOT be revoked
  });

  it('dispose() revokes the owned URL and detaches listeners', () => {
    const { el, player, revoked } = harness();
    player.load(fakeBlob());
    expect(el.listenerCount('ended')).toBe(1);
    player.dispose();
    expect(revoked).toEqual(['blob:fake-1']);
    expect(el.listenerCount('ended')).toBe(0);
    // events after dispose are ignored
    el.emit('error');
    expect(player.getState().status).not.toBe('error');
  });

  it('notifies subscribers and stops after unsubscribe', () => {
    const { el, player } = harness();
    const seen = vi.fn();
    const unsub = player.subscribe(seen);
    player.load(fakeBlob());
    expect(seen).toHaveBeenCalled();
    unsub();
    const before = seen.mock.calls.length;
    el.emit('loadedmetadata');
    expect(seen.mock.calls.length).toBe(before);
  });

  // --- B3-VOICE-FIGLASS-2: seek / seekBy (rich scrubber + skip controls) -----

  it('seek() jumps to an absolute position within duration', () => {
    const { el, player } = harness();
    player.load(fakeBlob());
    el.duration = 30;
    el.emit('loadedmetadata');
    player.seek(12);
    expect(el.currentTime).toBe(12);
    expect(player.getState().currentTime).toBe(12);
  });

  it('seek() clamps above duration and below zero', () => {
    const { el, player } = harness();
    player.load(fakeBlob());
    el.duration = 20;
    el.emit('loadedmetadata');
    player.seek(999);
    expect(player.getState().currentTime).toBe(20);
    player.seek(-5);
    expect(player.getState().currentTime).toBe(0);
  });

  it('seekBy() moves relative to the current position and clamps at the end', () => {
    const { el, player } = harness();
    player.load(fakeBlob());
    el.duration = 30;
    el.emit('loadedmetadata');
    player.seek(10);
    player.seekBy(10); // 20
    expect(player.getState().currentTime).toBe(20);
    player.seekBy(-15); // 5
    expect(player.getState().currentTime).toBe(5);
    player.seekBy(1000); // clamp -> 30
    expect(player.getState().currentTime).toBe(30);
  });

  it('seek() is a no-op before a source loads and after dispose', () => {
    const { el, player } = harness();
    player.seek(5); // no element yet
    expect(player.getState().currentTime).toBe(0);
    player.load(fakeBlob());
    player.dispose();
    player.seek(5);
    expect(el.currentTime).toBe(0);
  });
});

describe('clampSeekTarget', () => {
  it('forbids negatives and non-finite, clamps to duration when known', () => {
    expect(clampSeekTarget(-3, 10)).toBe(0);
    expect(clampSeekTarget(NaN, 10)).toBe(0);
    expect(clampSeekTarget(5, 10)).toBe(5);
    expect(clampSeekTarget(50, 10)).toBe(10);
  });

  it('allows any forward value while duration is unknown (0)', () => {
    expect(clampSeekTarget(120, 0)).toBe(120);
    expect(clampSeekTarget(-1, 0)).toBe(0);
  });
});
