// @vitest-environment jsdom
/**
 * AudioQueuePanel — header math + privacy notice contract.
 *
 * Pinned after the FIGLASS-18 staging smoke caught two papercuts:
 *  - the header said "1 audio · 0 B" for a transcribed artifact, because it
 *    counted the VISIBLE set but summed queue.totalBytes (the capacity
 *    metric: pending-only). The header must sum what the list shows.
 *  - the privacy notice was a permanent amber warning; it is recurring
 *    info — blue, and auto-hidden after privacyNoticeMs (default 35s).
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, act, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { AudioQueuePanel } from './AudioQueuePanel';
import type { UseAudioQueueReturn } from './useAudioQueue';
import type { AudioArtifact } from './audioArtifact';

function makeArtifact(overrides: Partial<AudioArtifact> = {}): AudioArtifact {
  return {
    id: 'a1',
    mime: 'audio/wav',
    size: 102400, // 100.0 KB
    durationMs: 32000,
    createdAt: '2026-06-12T00:00:00Z',
    updatedAt: '2026-06-12T00:00:00Z',
    state: 'transcribed',
    ...overrides,
  };
}

function makeQueue(artifacts: AudioArtifact[]): UseAudioQueueReturn {
  return {
    artifacts,
    // Capacity metric: pending-only — 0 here on purpose, the panel must NOT
    // use it for the header.
    totalBytes: 0,
    isLoading: false,
    transcribeArtifact: vi.fn(),
    retryTranscription: vi.fn(),
    getPlaybackUrl: vi.fn(async () => null),
    deleteArtifact: vi.fn(),
    clearTranscribed: vi.fn(),
    reload: vi.fn(),
  } as unknown as UseAudioQueueReturn;
}

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe('<AudioQueuePanel> header', () => {
  it('sums the bytes of the VISIBLE artifacts, transcribed included (no "0 B")', () => {
    const { container } = render(
      <AudioQueuePanel queue={makeQueue([makeArtifact()])} />,
    );
    expect(container.textContent).toContain('1 audio');
    expect(container.textContent).toContain('100.0 KB');
    expect(container.textContent).not.toContain('0 B');
  });
});

describe('<AudioQueuePanel> privacy notice', () => {
  it('renders as informational (blue) — not an amber warning', () => {
    const { container } = render(
      <AudioQueuePanel queue={makeQueue([makeArtifact()])} />,
    );
    const notice = container.querySelector('.fi-audio-queue-notice');
    expect(notice).toBeInTheDocument();
    expect(notice!.className).toContain('bg-blue-500/10');
    expect(notice!.className).not.toContain('yellow');
  });

  it('auto-hides after privacyNoticeMs', () => {
    vi.useFakeTimers();
    const { container } = render(
      <AudioQueuePanel queue={makeQueue([makeArtifact()])} privacyNoticeMs={35000} />,
    );
    expect(container.querySelector('.fi-audio-queue-notice')).toBeInTheDocument();

    act(() => { vi.advanceTimersByTime(35001); });

    expect(container.querySelector('.fi-audio-queue-notice')).not.toBeInTheDocument();
    // The queue itself stays — only the notice goes away.
    expect(container.textContent).toContain('1 audio');
  });

  it('privacyNoticeMs=0 keeps the notice forever', () => {
    vi.useFakeTimers();
    const { container } = render(
      <AudioQueuePanel queue={makeQueue([makeArtifact()])} privacyNoticeMs={0} />,
    );
    act(() => { vi.advanceTimersByTime(120000); });
    expect(container.querySelector('.fi-audio-queue-notice')).toBeInTheDocument();
  });
});
