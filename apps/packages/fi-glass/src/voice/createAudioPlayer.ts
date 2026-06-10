/**
 * fi-glass · audioPlayer — the reusable TTS *playback* engine (headless).
 *
 * The missing half of the voice stack: `useVoice`/SpeakButton resolve an
 * `AudioSource` (synthesis), but nothing in fi-glass actually PLAYS it — every
 * consumer (aurity, and next og118) had to re-wire its own <audio>, play/stop,
 * loading/error and object-URL cleanup. This engine owns that lifecycle once so
 * apps inherit it instead of re-implementing it.
 *
 * Deliberately framework-agnostic and dependency-injected: it talks to an
 * `AudioElementLike` (defaults to `new Audio()`) and to the object-URL helpers,
 * so the whole state machine — including URL-leak cleanup — is unit-testable in
 * node with a fake element and zero DOM. The React `useAudioPlayer` hook and the
 * `<AudioPlayer>` component are thin shells over this.
 *
 * Ownership rule (avoids the leak in useVoice.close): the engine revokes ONLY
 * the object URLs it created itself (from a Blob). A `{ url }` source is owned by
 * the caller / kept open for streaming, so it is never revoked here.
 */

import type { AudioSource } from '@free-intelligence/core';

export type AudioPlayerStatus =
  | 'idle'
  | 'loading'
  | 'playing'
  | 'paused'
  | 'error';

export interface AudioPlayerState {
  status: AudioPlayerStatus;
  isPlaying: boolean;
  isLoading: boolean;
  error: Error | null;
  /** The URL currently loaded into the element (object URL or external url). */
  currentSrc: string | null;
  /** Seconds; 0 until metadata loads. */
  duration: number;
  currentTime: number;
}

/**
 * The slice of HTMLAudioElement the engine touches. Real playback passes a
 * `new Audio()`; tests pass a fake that drives the same events synchronously.
 */
export interface AudioElementLike {
  src: string;
  currentTime: number;
  readonly duration: number;
  readonly paused: boolean;
  play(): Promise<void>;
  pause(): void;
  load(): void;
  addEventListener(type: string, listener: () => void): void;
  removeEventListener(type: string, listener: () => void): void;
}

export interface AudioPlayerDeps {
  /** Build the audio element. Default: `() => new Audio()` (browser only). */
  createElement?: () => AudioElementLike;
  /** Default: `URL.createObjectURL`. */
  createObjectURL?: (blob: Blob) => string;
  /** Default: `URL.revokeObjectURL`. */
  revokeObjectURL?: (url: string) => void;
}

export interface AudioPlayerOptions extends AudioPlayerDeps {
  /** Called on a playback/load error (app owns logging/reporting). */
  onError?: (error: unknown, context: string) => void;
  /** Called once when the current clip finishes. */
  onEnded?: () => void;
}

export interface AudioPlayerController {
  getState(): AudioPlayerState;
  /** Subscribe to state changes; returns an unsubscribe fn. */
  subscribe(listener: () => void): () => void;
  /** Point the player at a new source (revokes any previously-owned URL). */
  load(source: AudioSource): void;
  /** Start/resume playback of the loaded source. */
  play(): Promise<void>;
  pause(): void;
  /** Stop, rewind to 0 and release any owned object URL. */
  stop(): void;
  /** Play if paused/idle, pause if playing. */
  toggle(): Promise<void>;
  /** Tear down: detach listeners, pause, release owned URL. Idempotent. */
  dispose(): void;
}

const INITIAL: AudioPlayerState = {
  status: 'idle',
  isPlaying: false,
  isLoading: false,
  error: null,
  currentSrc: null,
  duration: 0,
  currentTime: 0,
};

function defaultCreateElement(): AudioElementLike {
  if (typeof Audio === 'undefined') {
    throw new Error(
      'createAudioPlayer: no Audio constructor available. Run in a browser, ' +
        'or inject `createElement` for non-DOM environments/tests.'
    );
  }
  return new Audio();
}

/** Is this source a Blob the engine must object-URL (and later revoke)? */
function isBlob(source: AudioSource): source is Blob {
  return typeof Blob !== 'undefined' && source instanceof Blob;
}

export function createAudioPlayer(
  options: AudioPlayerOptions = {}
): AudioPlayerController {
  const {
    createElement = defaultCreateElement,
    createObjectURL = (blob: Blob) => URL.createObjectURL(blob),
    revokeObjectURL = (url: string) => URL.revokeObjectURL(url),
    onError,
    onEnded,
  } = options;

  let state: AudioPlayerState = { ...INITIAL };
  let el: AudioElementLike | null = null;
  /** The object URL the engine created and is responsible for revoking. */
  let ownedUrl: string | null = null;
  let disposed = false;
  const listeners = new Set<() => void>();

  function emit(): void {
    for (const l of listeners) l();
  }

  function setState(patch: Partial<AudioPlayerState>): void {
    state = { ...state, ...patch };
    emit();
  }

  // --- element event handlers (attached once, on first ensureElement) -------
  const onLoadedMetadata = () => {
    setState({
      isLoading: false,
      duration: Number.isFinite(el?.duration) ? (el as AudioElementLike).duration : 0,
    });
  };
  const onTimeUpdate = () => {
    if (el) setState({ currentTime: el.currentTime });
  };
  const onPlaying = () => {
    setState({ status: 'playing', isPlaying: true, isLoading: false, error: null });
  };
  const onPause = () => {
    // 'ended' also fires a pause on some elements; the ended handler wins.
    if (state.status !== 'idle' && state.status !== 'error') {
      setState({ status: 'paused', isPlaying: false });
    }
  };
  const onEndedEvt = () => {
    setState({ status: 'idle', isPlaying: false, currentTime: 0 });
    onEnded?.();
  };
  const onErrorEvt = () => {
    const err = new Error('audio element error');
    setState({ status: 'error', isPlaying: false, isLoading: false, error: err });
    onError?.(err, 'audioPlayer:element');
  };

  function ensureElement(): AudioElementLike {
    if (el) return el;
    el = createElement();
    el.addEventListener('loadedmetadata', onLoadedMetadata);
    el.addEventListener('timeupdate', onTimeUpdate);
    el.addEventListener('playing', onPlaying);
    el.addEventListener('play', onPlaying);
    el.addEventListener('pause', onPause);
    el.addEventListener('ended', onEndedEvt);
    el.addEventListener('error', onErrorEvt);
    return el;
  }

  function releaseOwnedUrl(): void {
    if (ownedUrl) {
      revokeObjectURL(ownedUrl);
      ownedUrl = null;
    }
  }

  function load(source: AudioSource): void {
    if (disposed) return;
    const element = ensureElement();
    // Drop the previous owned URL before we lose the reference to it.
    releaseOwnedUrl();

    let url: string;
    if (isBlob(source)) {
      url = createObjectURL(source);
      ownedUrl = url; // engine owns it -> engine revokes it
    } else {
      url = source.url; // caller owns it -> never revoked here
    }

    element.src = url;
    element.load();
    setState({
      status: 'loading',
      isLoading: true,
      isPlaying: false,
      error: null,
      currentSrc: url,
      currentTime: 0,
      duration: 0,
    });
  }

  async function play(): Promise<void> {
    if (disposed || !el) return;
    try {
      await el.play();
      // 'play'/'playing' events set the playing state; set it here too so a
      // fake element that doesn't emit still reflects reality.
      setState({ status: 'playing', isPlaying: true, error: null });
    } catch (error) {
      setState({
        status: 'error',
        isPlaying: false,
        error: error instanceof Error ? error : new Error(String(error)),
      });
      onError?.(error, 'audioPlayer:play');
    }
  }

  function pause(): void {
    if (disposed || !el) return;
    el.pause();
    setState({ status: 'paused', isPlaying: false });
  }

  function stop(): void {
    if (disposed || !el) return;
    el.pause();
    el.currentTime = 0;
    el.src = '';
    releaseOwnedUrl();
    setState({
      status: 'idle',
      isPlaying: false,
      isLoading: false,
      currentSrc: null,
      currentTime: 0,
    });
  }

  async function toggle(): Promise<void> {
    if (state.isPlaying) {
      pause();
      return;
    }
    await play();
  }

  function dispose(): void {
    if (disposed) return;
    disposed = true;
    if (el) {
      el.pause();
      el.removeEventListener('loadedmetadata', onLoadedMetadata);
      el.removeEventListener('timeupdate', onTimeUpdate);
      el.removeEventListener('playing', onPlaying);
      el.removeEventListener('play', onPlaying);
      el.removeEventListener('pause', onPause);
      el.removeEventListener('ended', onEndedEvt);
      el.removeEventListener('error', onErrorEvt);
    }
    releaseOwnedUrl();
    listeners.clear();
  }

  return {
    getState: () => state,
    subscribe(listener: () => void) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    load,
    play,
    pause,
    stop,
    toggle,
    dispose,
  };
}
