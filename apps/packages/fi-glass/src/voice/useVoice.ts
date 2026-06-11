'use client';

/**
 * fi-glass · useVoice — TTS orchestration that consumes a VoiceAdapter.
 *
 * Drop-in compatible with aurity's former useAudioPlayer (same return shape),
 * but every synthesis goes through `adapter.synthesize` instead of a hardcoded
 * endpoint. fi-glass stays backend-agnostic; the app's adapter owns the I/O,
 * auth, provider routing and any state-machine/consent logic INSIDE synthesize.
 *
 * Resolves AudioSource transparently: a Blob is object-URL'd, a { url } is used
 * as-is (keeps streaming TTS open).
 *
 * B3-VOICE-FIGLASS-6 — single-flight: while a synthesis is in flight, further
 * generateAudio/changeVoice calls are IGNORED. The daily-driver audit caught the
 * cost bug this guards: TTS latency is seconds, the SpeakButton gave no busy
 * feedback, and every extra click fired another PAID provider request (~50 spam
 * clicks = ~50 synthesis charges). The ref-based guard is synchronous, so even
 * same-tick double-clicks collapse to one request.
 *
 * B3-VOICE-FIGLASS-7 — session synthesis cache: re-asking for the SAME text+voice
 * no longer re-bills the provider. A bounded LRU keeps the last few clips as
 * BLOBS in hook memory (never the object URL — its lifecycle is fragile; a fresh
 * URL is minted per playback and revoked by the normal replace/close paths, so
 * eviction never has a URL to leak). Deliberately memory-only: NO IndexedDB, NO
 * localStorage, NO Cache API — audio must not outlive the page (the audit
 * contract: conversations persist, audio/blobs never do). A reload therefore
 * clears the cache naturally, and re-listening after reload is a new paid
 * synthesis BY DESIGN. Errors and empty results are never cached.
 */

import { useCallback, useRef, useState } from 'react';
import type { VoiceAdapter, AudioSource } from '@free-intelligence/core';

export interface UseVoiceOptions {
  /** Called when synthesis fails (app decides logging/reporting). */
  onError?: (error: unknown, context: string) => void;
}

export interface UseVoiceReturn {
  isOpen: boolean;
  isLoading: boolean;
  audioUrl: string | null;
  voiceName: string;
  isUserMessage: boolean;
  currentVoice: string;
  currentText: string;
  generateAudio: (text: string, voice?: string, isUser?: boolean) => Promise<void>;
  changeVoice: (newVoice: string) => Promise<void>;
  close: () => void;
  /**
   * Whether `text` (+`voice`, default 'nova') is already in the session cache —
   * i.e. clicking Speak would replay instantly and bill nothing. Lets the UI
   * tell "will synthesize (paid, seconds)" apart from "already generated"
   * (B3-VOICE-FIGLASS-8). Render-time freshness is guaranteed by the state
   * updates every synthesis already makes (isLoading/audioUrl).
   */
  hasCachedAudio: (text: string, voice?: string) => boolean;
}

/** Blob -> object URL; { url } -> url. */
function toUrl(src: AudioSource): string {
  return src instanceof Blob ? URL.createObjectURL(src) : src.url;
}

/** Max clips the per-hook session cache retains (LRU evicts beyond this). */
export const TTS_CACHE_MAX_CLIPS = 8;

/** Cache key: voice + exact text. The cache lives per hook instance, and a hook
 * is bound to ONE adapter (= one provider/deployment/format), so the adapter's
 * routing never needs to be part of the key. */
const clipKey = (text: string, voice: string) => `${voice}\u0000${text}`;

export function useVoice(
  adapter: VoiceAdapter | undefined,
  opts: UseVoiceOptions = {}
): UseVoiceReturn {
  const { onError } = opts;
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [voiceName, setVoiceName] = useState('nova');
  const [isUserMessage, setIsUserMessage] = useState(false);
  const [currentVoice, setCurrentVoice] = useState('nova');
  const [currentText, setCurrentText] = useState('');
  // Synchronous in-flight latch (state lags a tick; the ref doesn't, so rapid
  // repeat clicks can never fan out into parallel paid synthesize calls).
  const inFlight = useRef(false);
  // Session LRU of synthesized clips (B3-VOICE-FIGLASS-7). Blobs only — see the
  // module docblock for why neither object URLs nor any persistent storage.
  const clipCache = useRef(new Map<string, Blob>());

  // Cache-aware synthesis: hit returns the cached Blob (refreshed as most
  // recent, NO provider call); miss bills the provider once and caches a
  // successful non-empty Blob. `{ url }` sources (streaming TTS) pass through
  // uncached — they may be ephemeral and aren't re-billable artifacts we hold.
  const synthesizeCached = useCallback(
    async (text: string, voice: string): Promise<AudioSource> => {
      const cache = clipCache.current;
      const key = clipKey(text, voice);
      const hit = cache.get(key);
      if (hit) {
        cache.delete(key);
        cache.set(key, hit); // LRU refresh
        return hit;
      }
      const src = await adapter!.synthesize!(text, voice);
      if (src instanceof Blob && src.size > 0) {
        cache.set(key, src);
        while (cache.size > TTS_CACHE_MAX_CLIPS) {
          const oldest = cache.keys().next().value;
          if (oldest === undefined) break;
          cache.delete(oldest);
        }
      }
      return src;
    },
    [adapter],
  );

  const getVoiceDisplayName = useCallback(
    (voiceId: string): string => {
      const found = adapter?.availableVoices?.find((v) => v.id === voiceId);
      if (found) return found.label.split(' ')[0];
      const match = voiceId.match(/([A-Z][a-z]+)Neural$/);
      return match ? match[1] : voiceId;
    },
    [adapter]
  );

  const generateAudio = useCallback(
    async (text: string, voice: string = 'nova', isUser: boolean = false) => {
      if (!adapter?.synthesize) return;
      if (inFlight.current) return; // single-flight: spam clicks are no-ops
      inFlight.current = true;
      setCurrentText(text);
      setCurrentVoice(voice);
      setIsUserMessage(isUser);
      setVoiceName(getVoiceDisplayName(voice));

      setIsOpen(true);
      setAudioUrl((prev) => {
        // Don't leak the previous clip's object URL when re-generating.
        if (prev?.startsWith('blob:')) URL.revokeObjectURL(prev);
        return null;
      });

      // Cache hit resolves synchronously-ish: skip the loading state entirely so
      // a re-listen doesn't flash a spinner for a clip we already hold.
      const isHit = clipCache.current.has(clipKey(text, voice));
      if (!isHit) setIsLoading(true);

      try {
        const src = await synthesizeCached(text, voice);
        setAudioUrl(toUrl(src));
      } catch (error) {
        onError?.(error, 'useVoice:TTS');
        setIsOpen(false);
      } finally {
        inFlight.current = false;
        setIsLoading(false);
      }
    },
    [adapter, getVoiceDisplayName, onError, synthesizeCached]
  );

  const changeVoice = useCallback(
    async (newVoice: string) => {
      if (!currentText || !adapter?.synthesize) return;
      if (inFlight.current) return; // single-flight (same paid-request guard)
      inFlight.current = true;
      setCurrentVoice(newVoice);
      setVoiceName(getVoiceDisplayName(newVoice));
      setIsLoading(true);

      if (audioUrl) URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);

      try {
        const src = await synthesizeCached(currentText, newVoice);
        setAudioUrl(toUrl(src));
      } catch (error) {
        onError?.(error, 'useVoice:VoiceChange');
      } finally {
        inFlight.current = false;
        setIsLoading(false);
      }
    },
    [adapter, audioUrl, currentText, getVoiceDisplayName, onError, synthesizeCached]
  );

  const close = useCallback(() => {
    setIsOpen(false);
    setAudioUrl(null);
    setIsLoading(false);
    setCurrentText('');
    setIsUserMessage(false);
  }, []);

  const hasCachedAudio = useCallback(
    (text: string, voice: string = 'nova') =>
      clipCache.current.has(clipKey(text, voice)),
    [],
  );

  return {
    isOpen,
    isLoading,
    audioUrl,
    voiceName,
    isUserMessage,
    currentVoice,
    currentText,
    generateAudio,
    changeVoice,
    close,
    hasCachedAudio,
  };
}
