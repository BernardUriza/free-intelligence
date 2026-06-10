'use client';

/**
 * fi-glass · useAudioPlayer — React shell over the headless `createAudioPlayer`.
 *
 * Owns one controller per mount, subscribes the component to its state via
 * useSyncExternalStore, and disposes it on unmount (so every owned object URL is
 * revoked — no leaks even if the component dies mid-clip). The state machine and
 * cleanup live in audioPlayer.ts; this file is just the React binding.
 *
 * Pairs with `useVoice` (synthesis) and `SpeakButton` (trigger): an app does
 *   const { generateAudio, ... } = useVoice(adapter)   // text -> AudioSource
 *   const player = useAudioPlayer()                     // AudioSource -> sound
 * or, for the common case, feeds an AudioSource straight to `playSource`.
 */

import { useEffect, useMemo, useRef, useSyncExternalStore } from 'react';
import type { AudioSource } from '@free-intelligence/core';
import {
  createAudioPlayer,
  type AudioPlayerOptions,
  type AudioPlayerState,
} from './createAudioPlayer';

export interface UseAudioPlayerOptions {
  onError?: (error: unknown, context: string) => void;
  onEnded?: () => void;
  /**
   * Dependency overrides forwarded to the engine. Apps never need these; tests
   * and non-DOM environments inject a fake element / URL helpers.
   */
  deps?: Pick<
    AudioPlayerOptions,
    'createElement' | 'createObjectURL' | 'revokeObjectURL'
  >;
}

export interface UseAudioPlayerReturn extends AudioPlayerState {
  /** Point the player at a source without starting it. */
  load: (source: AudioSource) => void;
  play: () => Promise<void>;
  pause: () => void;
  stop: () => void;
  toggle: () => Promise<void>;
  /** Convenience: load a source and immediately play it. */
  playSource: (source: AudioSource) => Promise<void>;
}

export function useAudioPlayer(
  opts: UseAudioPlayerOptions = {}
): UseAudioPlayerReturn {
  // Keep the latest callbacks without re-creating the controller each render.
  const cbRef = useRef(opts);
  cbRef.current = opts;

  const controller = useMemo(
    () =>
      createAudioPlayer({
        onError: (e, ctx) => cbRef.current.onError?.(e, ctx),
        onEnded: () => cbRef.current.onEnded?.(),
        ...opts.deps,
      }),
    // One controller for the component's lifetime; deps are read once by design.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  useEffect(() => () => controller.dispose(), [controller]);

  const state = useSyncExternalStore(
    controller.subscribe,
    controller.getState,
    controller.getState
  );

  return {
    ...state,
    load: controller.load,
    play: controller.play,
    pause: controller.pause,
    stop: controller.stop,
    toggle: controller.toggle,
    playSource: async (source: AudioSource) => {
      controller.load(source);
      await controller.play();
    },
  };
}
