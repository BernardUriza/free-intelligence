// @vitest-environment jsdom
/**
 * AudioQueueItem — playback releases its object URL and its audio element when
 * the row goes away mid-play, not only on `ended`/`error` (FIGLASS-STATE-RESIDUALS-1 #4).
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { act, cleanup, fireEvent, render } from '@testing-library/react';
import { AudioQueueItem } from './AudioQueueItem';
import type { AudioArtifact } from './audioArtifact';

const artifact: AudioArtifact = {
  id: 'a1',
  mime: 'audio/wav',
  size: 1024,
  durationMs: 3000,
  createdAt: '2026-10-19T00:00:00Z',
  updatedAt: '2026-10-19T00:00:00Z',
  state: 'queued',
};

class FakeAudio {
  static made: FakeAudio[] = [];
  pause = vi.fn();
  play = vi.fn(async () => {});
  addEventListener = vi.fn();
  constructor(public src: string) {
    FakeAudio.made.push(this);
  }
}

describe('<AudioQueueItem> playback cleanup', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    FakeAudio.made = [];
  });

  it('unmounting mid-play stops the audio and revokes its URL', async () => {
    vi.stubGlobal('Audio', FakeAudio);
    const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    const { getByLabelText, unmount } = render(
      <AudioQueueItem artifact={artifact} onGetPlaybackUrl={async () => 'blob:clip-1'} />,
    );
    await act(async () => {
      fireEvent.click(getByLabelText('Reproducir'));
    });
    expect(FakeAudio.made).toHaveLength(1);

    unmount();
    expect(FakeAudio.made[0].pause).toHaveBeenCalled();
    expect(revoke).toHaveBeenCalledWith('blob:clip-1');
    revoke.mockRestore();
  });

  it('pause then play resumes the same clip instead of minting a second URL', async () => {
    vi.stubGlobal('Audio', FakeAudio);
    const getUrl = vi.fn(async () => 'blob:clip-1');
    const { getByLabelText } = render(<AudioQueueItem artifact={artifact} onGetPlaybackUrl={getUrl} />);
    await act(async () => {
      fireEvent.click(getByLabelText('Reproducir'));
    });
    await act(async () => {
      fireEvent.click(getByLabelText('Pausar'));
    });
    await act(async () => {
      fireEvent.click(getByLabelText('Reproducir'));
    });
    expect(getUrl).toHaveBeenCalledTimes(1);
    expect(FakeAudio.made).toHaveLength(1);
  });
});
