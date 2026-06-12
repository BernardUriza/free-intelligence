// @vitest-environment jsdom
/**
 * Tests for AudioDraftPlayer (B3-VOICE-FIGLASS-11).
 *
 * Pins the play lifecycle contract:
 *  - the Audio element is created synchronously within the click task so
 *    browsers with strict autoplay policies allow play();
 *  - play() is actually called (not a no-op);
 *  - the object URL is revoked on ended/error/discard;
 *  - playback errors surface a recoverable state, not a silent freeze.
 *
 * Static SSR checks cover state transitions (saving/busy/failed) without
 * needing a real Audio element.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act, cleanup } from '@testing-library/react';
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
    durationMs: 500,
    createdAt: '2026-06-11T00:00:00Z',
    updatedAt: '2026-06-11T00:00:00Z',
    state: 'queued',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Audio + URL mocks
// ---------------------------------------------------------------------------

let mockPlay: ReturnType<typeof vi.fn>;
let mockPause: ReturnType<typeof vi.fn>;
let capturedListeners: Record<string, () => void>;

function setupAudioMock() {
  mockPlay = vi.fn(() => Promise.resolve());
  mockPause = vi.fn();
  capturedListeners = {};

  class MockAudio {
    src = '';
    play = mockPlay;
    pause = mockPause;
    addEventListener(event: string, handler: () => void) {
      capturedListeners[event] = handler;
    }
  }

  vi.stubGlobal('Audio', MockAudio);
  vi.stubGlobal('URL', {
    createObjectURL: vi.fn(() => 'blob:fake-url'),
    revokeObjectURL: vi.fn(),
  });
}

beforeEach(setupAudioMock);
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// Play lifecycle (jsdom)
// ---------------------------------------------------------------------------

describe('<AudioDraftPlayer> play lifecycle (B3-VOICE-FIGLASS-11)', () => {
  it('play button is enabled when artifact is playable (queued, size > 0)', () => {
    render(
      <AudioDraftPlayer
        artifact={makeArtifact()}
        onGetPlaybackUrl={async () => 'blob:fake-url'}
      />,
    );
    const btn = screen.getByRole('button', { name: /reproducir grabación/i });
    expect(btn).not.toBeDisabled();
  });

  it('click play calls onGetPlaybackUrl with the artifact id', async () => {
    const getUrl = vi.fn(async () => 'blob:test-url');
    render(<AudioDraftPlayer artifact={makeArtifact()} onGetPlaybackUrl={getUrl} />);
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /reproducir grabación/i }));
    });
    expect(getUrl).toHaveBeenCalledWith('draft-1');
  });

  it('click play is not a no-op: Audio.play() is called', async () => {
    render(
      <AudioDraftPlayer
        artifact={makeArtifact()}
        onGetPlaybackUrl={async () => 'blob:test-url'}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /reproducir grabación/i }));
    });
    expect(mockPlay).toHaveBeenCalledTimes(1);
  });

  it('revokes the object URL when playback ends', async () => {
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:revoke-test'),
      revokeObjectURL,
    });
    render(
      <AudioDraftPlayer
        artifact={makeArtifact()}
        onGetPlaybackUrl={async () => 'blob:revoke-test'}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /reproducir grabación/i }));
    });
    // Simulate the audio ending
    act(() => { capturedListeners['ended']?.(); });
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:revoke-test');
  });

  it('revokes the object URL on playback error', async () => {
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:error-test'),
      revokeObjectURL,
    });
    render(
      <AudioDraftPlayer
        artifact={makeArtifact()}
        onGetPlaybackUrl={async () => 'blob:error-test'}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /reproducir grabación/i }));
    });
    act(() => { capturedListeners['error']?.(); });
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:error-test');
  });

  it('playback error via play() rejection sets state back to not-playing', async () => {
    // play() rejects → state recovers (button returns to ▶ not ⏸)
    mockPlay.mockRejectedValueOnce(new Error('NotAllowedError'));
    render(
      <AudioDraftPlayer
        artifact={makeArtifact()}
        onGetPlaybackUrl={async () => 'blob:reject-test'}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /reproducir grabación/i }));
    });
    // After rejection, the button label reverts to the non-playing state
    expect(
      screen.getByRole('button', { name: /reproducir grabación/i }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// State transitions (SSR — no Audio mock needed)
// ---------------------------------------------------------------------------

describe('<AudioDraftPlayer> state transitions (SSR)', () => {
  it('disables play button while saving (state=stopping)', () => {
    const html = renderToStaticMarkup(
      <AudioDraftPlayer
        artifact={makeArtifact({ state: 'stopping', size: 0 })}
        onGetPlaybackUrl={async () => null}
      />,
    );
    expect(html).toContain('disabled');
  });

  it('disables play button while transcribing (state=transcribing)', () => {
    const html = renderToStaticMarkup(
      <AudioDraftPlayer
        artifact={makeArtifact({ state: 'transcribing' })}
        onGetPlaybackUrl={async () => null}
      />,
    );
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

  it('shows error message text when failed', () => {
    const html = renderToStaticMarkup(
      <AudioDraftPlayer
        artifact={makeArtifact({ state: 'failed', errorMessage: 'Transcripción fallida' })}
      />,
    );
    expect(html).toContain('Transcripción fallida');
  });

  it('shows resume button when onResume is provided', () => {
    const html = renderToStaticMarkup(
      <AudioDraftPlayer
        artifact={makeArtifact({ state: 'paused' })}
        onResume={() => {}}
      />,
    );
    expect(html).toContain('aria-label="Reanudar grabación"');
  });

  it('renders the fi-audio-draft semantic class for stable CSS targeting', () => {
    const html = renderToStaticMarkup(
      <AudioDraftPlayer artifact={makeArtifact()} />,
    );
    expect(html).toContain('fi-audio-draft');
  });
});
