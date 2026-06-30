/**
 * createAudioCuePlayer — the thin Web Audio adapter behind resonanceCueController.
 *
 * Pre-decodes the three cue buffers and plays them with the low latency only the
 * Web Audio API gives (AudioBufferSourceNode, not <audio>). It knows nothing about
 * the FSM — it just plays, loops, and stops. stopLoop/stopAll are best-effort so a
 * teardown never throws, and one-shots self-evict on ended so they can overlap
 * without leaking nodes.
 */

import type { ResonanceCuePlayer } from './resonanceCueController';

export interface AudioCueAssets {
  thinking: string;
  crystalline: string;
  ready: string;
}

export interface AudioCuePlayerOptions {
  volume?: number;
}

export interface AudioCuePlayer extends ResonanceCuePlayer {
  preload: () => Promise<void>;
  /** Resume the AudioContext from a user gesture (the call button). Returns the state. */
  resume: () => Promise<string>;
  dispose: () => void;
}

type CueName = 'thinking' | 'crystalline' | 'ready';

export function createAudioCuePlayer(
  assets: AudioCueAssets,
  options: AudioCuePlayerOptions = {},
): AudioCuePlayer {
  const { volume = 0.6 } = options;
  let ctx: AudioContext | null = null;
  let gain: GainNode | null = null;
  const buffers = new Map<CueName, AudioBuffer>();
  const loops = new Map<'thinking', AudioBufferSourceNode>();
  const oneShots = new Set<AudioBufferSourceNode>();

  function ensureContext(): AudioContext | null {
    if (typeof window === 'undefined') return null;
    if (!ctx) {
      const Ctor = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!Ctor) return null;
      ctx = new Ctor();
      gain = ctx.createGain();
      gain.gain.value = volume;
      gain.connect(ctx.destination);
    }
    if (ctx.state === 'suspended') void ctx.resume();
    return ctx;
  }

  async function preload() {
    const c = ensureContext();
    if (!c) return;
    const entries = Object.entries(assets) as Array<[CueName, string]>;
    await Promise.all(
      entries.map(async ([name, url]) => {
        if (buffers.has(name)) return;
        try {
          const res = await fetch(url);
          const arr = await res.arrayBuffer();
          buffers.set(name, await c.decodeAudioData(arr));
        } catch (e) {
          console.warn(`[resonance] cue preload failed: ${name}`, e);
        }
      }),
    );
  }

  function source(name: CueName, loop: boolean): AudioBufferSourceNode | null {
    const c = ensureContext();
    const buf = buffers.get(name);
    if (!c || !gain || !buf) return null;
    const src = c.createBufferSource();
    src.buffer = buf;
    src.loop = loop;
    src.connect(gain);
    return src;
  }

  function stopLoop(cue: 'thinking') {
    const src = loops.get(cue);
    if (!src) return;
    loops.delete(cue);
    try { src.stop(); } catch { /* already stopped */ }
  }

  return {
    preload,
    resume: async () => {
      const c = ensureContext();
      if (c && c.state === 'suspended') await c.resume();
      return c?.state ?? 'none';
    },
    playOnce: (cue) => {
      const src = source(cue, false);
      if (!src) return;
      oneShots.add(src);
      src.onended = () => oneShots.delete(src);
      try { src.start(); } catch { oneShots.delete(src); }
    },
    playLoop: (cue) => {
      if (loops.has(cue)) return; // idempotent — controller also guards, defence in depth
      const src = source(cue, true);
      if (!src) return;
      loops.set(cue, src);
      try { src.start(); } catch { loops.delete(cue); }
    },
    stopLoop,
    stopAll: () => {
      for (const cue of [...loops.keys()]) stopLoop(cue);
      for (const src of [...oneShots]) { try { src.stop(); } catch { /* noop */ } }
      oneShots.clear();
    },
    dispose: () => {
      for (const cue of [...loops.keys()]) stopLoop(cue);
      for (const src of [...oneShots]) { try { src.stop(); } catch { /* noop */ } }
      oneShots.clear();
      buffers.clear();
      void ctx?.close();
      ctx = null;
      gain = null;
    },
  };
}
