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
 *  - a PAUSED recording with a pausedPreview (segmented pause, FIGLASS-18)
 *    plays everything recorded so far through the SAME rich player;
 *  - a PAUSED recording WITHOUT a preview (still splicing / not wired) falls
 *    back to an honest status (recorded time + "Grabación en pausa" + Resume)
 *    with NO dead play control;
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
// Paused recording with a preview → plays back the recorded-so-far audio
// ---------------------------------------------------------------------------

describe('<AudioDraftPlayer> paused with preview (B3-VOICE-FIGLASS-18)', () => {
  const preview = new Blob(['wav'], { type: 'audio/wav' });
  const pausedWithPreviewHtml = renderToStaticMarkup(
    <AudioDraftPlayer
      artifact={makeArtifact({ state: 'paused', size: 0, durationMs: 9835 })}
      pausedPreview={preview}
      onResume={() => {}}
    />,
  );

  it('renders the rich player primitive for the recorded-so-far audio', () => {
    expect(pausedWithPreviewHtml).toContain('data-fi-audio-player="rich"');
    expect(pausedWithPreviewHtml).toContain('data-fi-audio-progress');
  });

  it('keeps signalling the open session: pulsing dot + Resume', () => {
    expect(pausedWithPreviewHtml).toContain('fi-audio-draft-pauseddot');
    expect(pausedWithPreviewHtml).toContain('aria-label="Reanudar grabación"');
  });

  it('loads the preview blob into the player on mount (jsdom)', async () => {
    const createObjectURL = vi.fn(() => 'blob:preview-url');
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL: vi.fn() });
    await act(async () => {
      render(
        <AudioDraftPlayer
          artifact={makeArtifact({ state: 'paused', size: 0 })}
          pausedPreview={preview}
          onResume={() => {}}
        />,
      );
    });
    expect(createObjectURL).toHaveBeenCalledWith(preview);
  });
});

// ---------------------------------------------------------------------------
// Paused recording without a preview → honest status, no dead controls (SSR)
// ---------------------------------------------------------------------------

describe('<AudioDraftPlayer> paused without preview (B3-VOICE-FIGLASS-17/18)', () => {
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

  it('renders NO player and NO dead play control while the preview is absent', () => {
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

describe('<AudioDraftPlayer> variant (COMPOSER-FRAME-2)', () => {
  it('defaults to the card chrome (standalone frosted card)', () => {
    const html = renderToStaticMarkup(<AudioDraftPlayer artifact={makeArtifact()} />);
    expect(html).toContain('rounded-2xl');
    expect(html).toContain('backdrop-blur-xl');
    expect(html).not.toContain('fi-audio-draft--row');
  });

  it('renders the bare row chrome inside a composer frame (variant="row")', () => {
    const html = renderToStaticMarkup(
      <AudioDraftPlayer artifact={makeArtifact()} variant="row" />,
    );
    expect(html).toContain('fi-audio-draft--row');
    expect(html).not.toContain('rounded-2xl');
    expect(html).not.toContain('backdrop-blur-xl');
    expect(html).not.toContain('shadow-lg');
  });
});

// ---------------------------------------------------------------------------
// Mobile-first row: compact transport keeps the primary action on-screen
// (CONV-MOBILE-RECLAIM — the "no visible Transcribir button" bug)
// ---------------------------------------------------------------------------

describe('<AudioDraftPlayer> compact row transport (CONV-MOBILE-RECLAIM)', () => {
  it('drops the ±10s skip and stop controls in the in-composer row', () => {
    const html = renderToStaticMarkup(
      <AudioDraftPlayer
        artifact={makeArtifact()}
        variant="row"
        onPrimary={() => {}}
      />,
    );
    // Compact player keeps only play/pause + scrubber; the width-hungry skip and
    // stop buttons are gone so the primary action is never crowded off-screen.
    expect(html).toContain('aria-label="Reproducir audio"');
    expect(html).toContain('data-fi-audio-progress');
    expect(html).not.toContain('aria-label="Retroceder 10 segundos"');
    expect(html).not.toContain('aria-label="Avanzar 10 segundos"');
    expect(html).not.toContain('aria-label="Detener audio"');
  });

  it('keeps the primary (Transcribir) action rendered in the compact row', () => {
    const html = renderToStaticMarkup(
      <AudioDraftPlayer
        artifact={makeArtifact()}
        variant="row"
        onPrimary={() => {}}
        primaryActionLabel="Transcribir"
      />,
    );
    expect(html).toContain('fi-audio-draft-primary');
    expect(html).toContain('Transcribir');
  });

  it('keeps the FULL transport (skip + stop) for the standalone card', () => {
    const html = renderToStaticMarkup(
      <AudioDraftPlayer artifact={makeArtifact()} onPrimary={() => {}} />,
    );
    expect(html).toContain('aria-label="Retroceder 10 segundos"');
    expect(html).toContain('aria-label="Detener audio"');
    expect(html).toContain('aria-label="Avanzar 10 segundos"');
  });
});
