// @vitest-environment jsdom
/**
 * Tests for AudioDraftPlayer (B3-VOICE-FIGLASS-11 + B3-VOICE-FIGLASS-17).
 *
 * FIGLASS-17 replaced the home-grown mini-player with RichAudioPlayer — the
 * same primitive TTS playback uses — so the transport/seek behavior is covered
 * at the engine level (createAudioPlayer.test.ts). What this suite pins is the
 * DRAFT contract:
 *  - a playable draft renders the rich player (skip ±10s + scrubber), not
 *    decorative bars;
 *  - the playback URL is resolved per artifact and revoked on unmount;
 *  - a PAUSED recording shows an honest status (recorded time + "Grabación en
 *    pausa" + Resume) with NO dead play control and NO player (RecordRTC has
 *    no partial blob mid-recording);
 *  - state transitions (saving/busy/failed) stay visible and recoverable.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, act, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { AudioDraftPlayer } from './AudioDraftPlayer';
import type { AudioArtifact } from './audioArtifact';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeArtifact(overrides: Partial<AudioArtifact> = {}): AudioArtifact {
  return {
    id: 'draft-1',
    mime: 'audio/wav',
    size: 25600,
    durationMs: 9835,
    createdAt: '2026-06-11T00:00:00Z',
    updatedAt: '2026-06-11T00:00:00Z',
    state: 'queued',
    ...overrides,
  };
}

// Minimal media element for the player engine under jsdom (jsdom's
// HTMLMediaElement.load/play are not implemented).
class MockAudio {
  src = '';
  currentTime = 0;
  duration = 0;
  paused = true;
  play = vi.fn(() => Promise.resolve());
  pause = vi.fn();
  load = vi.fn();
  addEventListener = vi.fn();
  removeEventListener = vi.fn();
}

beforeEach(() => {
  vi.stubGlobal('Audio', MockAudio);
  vi.stubGlobal('URL', {
    createObjectURL: vi.fn(() => 'blob:fake-url'),
    revokeObjectURL: vi.fn(),
  });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// Playable draft → the TTS primitive (jsdom)
// ---------------------------------------------------------------------------

describe('<AudioDraftPlayer> playable draft (B3-VOICE-FIGLASS-17)', () => {
  it('renders the rich player primitive (same as TTS) for a queued draft', () => {
    const { container } = render(
      <AudioDraftPlayer
        artifact={makeArtifact()}
        onGetPlaybackUrl={async () => 'blob:fake-url'}
      />,
    );
    expect(
      container.querySelector('[data-fi-audio-player="rich"]'),
    ).toBeInTheDocument();
    expect(container.querySelector('[data-fi-audio-progress]')).toBeInTheDocument();
  });

  it('resolves the playback URL with the artifact id on mount', async () => {
    const getUrl = vi.fn(async () => 'blob:test-url');
    await act(async () => {
      render(<AudioDraftPlayer artifact={makeArtifact()} onGetPlaybackUrl={getUrl} />);
    });
    expect(getUrl).toHaveBeenCalledWith('draft-1');
  });

  it('revokes the resolved object URL on unmount', async () => {
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:revoke-test'),
      revokeObjectURL,
    });
    let unmount!: () => void;
    await act(async () => {
      ({ unmount } = render(
        <AudioDraftPlayer
          artifact={makeArtifact()}
          onGetPlaybackUrl={async () => 'blob:revoke-test'}
        />,
      ));
    });
    act(() => unmount());
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:revoke-test');
  });

  it('does not resolve a URL while the artifact is still saving (size 0)', async () => {
    const getUrl = vi.fn(async () => 'blob:never');
    await act(async () => {
      render(
        <AudioDraftPlayer
          artifact={makeArtifact({ state: 'stopping', size: 0 })}
          onGetPlaybackUrl={getUrl}
        />,
      );
    });
    expect(getUrl).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// Paused recording → honest status, no dead controls (SSR)
// ---------------------------------------------------------------------------

describe('<AudioDraftPlayer> paused recording (B3-VOICE-FIGLASS-17)', () => {
  const pausedHtml = renderToStaticMarkup(
    <AudioDraftPlayer
      artifact={makeArtifact({ state: 'paused', size: 0, durationMs: 9835 })}
      onResume={() => {}}
    />,
  );

  it('shows the recorded-so-far time instead of "--:--"', () => {
    expect(pausedHtml).toContain('00:09');
    expect(pausedHtml).not.toContain('--:--');
  });

  it('labels the state and offers Resume', () => {
    expect(pausedHtml).toContain('Grabación en pausa');
    expect(pausedHtml).toContain('aria-label="Reanudar grabación"');
  });

  it('renders NO player and NO dead play control while paused', () => {
    expect(pausedHtml).not.toContain('data-fi-audio-player');
    expect(pausedHtml).not.toContain('fi-audio-draft-play"');
  });
});

// ---------------------------------------------------------------------------
// State transitions (SSR)
// ---------------------------------------------------------------------------

describe('<AudioDraftPlayer> state transitions (SSR)', () => {
  it('shows the saving state while stopping', () => {
    const html = renderToStaticMarkup(
      <AudioDraftPlayer artifact={makeArtifact({ state: 'stopping', size: 0 })} />,
    );
    expect(html).toContain('Guardando…');
  });

  it('disables the primary action while transcribing', () => {
    const html = renderToStaticMarkup(
      <AudioDraftPlayer
        artifact={makeArtifact({ state: 'transcribing' })}
        onPrimary={() => {}}
      />,
    );
    expect(html).toContain('Transcribiendo…');
    expect(html).toContain('disabled');
  });

  it('shows retry button (recoverable state) when failed with onRetry', () => {
    const html = renderToStaticMarkup(
      <AudioDraftPlayer
        artifact={makeArtifact({ state: 'failed', errorMessage: 'Error de red' })}
        onRetry={() => {}}
      />,
    );
    expect(html).toContain('aria-label="Reintentar"');
  });

  it('announces the error message when failed', () => {
    const html = renderToStaticMarkup(
      <AudioDraftPlayer
        artifact={makeArtifact({ state: 'failed', errorMessage: 'Transcripción fallida' })}
      />,
    );
    expect(html).toContain('Transcripción fallida');
    expect(html).toContain('role="alert"');
  });

  it('renders the fi-audio-draft semantic class for stable CSS targeting', () => {
    const html = renderToStaticMarkup(<AudioDraftPlayer artifact={makeArtifact()} />);
    expect(html).toContain('fi-audio-draft');
  });
});
