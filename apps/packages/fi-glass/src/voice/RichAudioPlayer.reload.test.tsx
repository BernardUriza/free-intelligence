// @vitest-environment jsdom
/**
 * Regression: the load effect keys on the source's VALUE, not object identity.
 *
 * Call sites build `{ url }` inline, so every parent re-render passes a NEW
 * object for the SAME audio. Identity-keyed loading re-ran load() per render,
 * resetting playback to 0 mid-listen (and restarting it under autoPlay). These
 * tests pin the contract: same url across re-renders → ONE load; a different
 * url (or a different Blob) → a new load.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import { RichAudioPlayer } from './RichAudioPlayer';

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

const created: MockAudio[] = [];
const totalLoads = () => created.reduce((n, el) => n + el.load.mock.calls.length, 0);

beforeEach(() => {
  created.length = 0;
  vi.stubGlobal(
    'Audio',
    class extends MockAudio {
      constructor() {
        super();
        created.push(this);
      }
    }
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('<RichAudioPlayer> source value keying', () => {
  it('does NOT reload when a re-render passes a new object with the same url', () => {
    const { rerender } = render(<RichAudioPlayer source={{ url: 'blob:a' }} />);
    const after1 = totalLoads();
    expect(after1).toBeGreaterThan(0);
    rerender(<RichAudioPlayer source={{ url: 'blob:a' }} />);
    rerender(<RichAudioPlayer source={{ url: 'blob:a' }} />);
    expect(totalLoads()).toBe(after1);
  });

  it('reloads when the url actually changes', () => {
    const { rerender } = render(<RichAudioPlayer source={{ url: 'blob:a' }} />);
    const after1 = totalLoads();
    rerender(<RichAudioPlayer source={{ url: 'blob:b' }} />);
    expect(totalLoads()).toBeGreaterThan(after1);
  });

  it('keys a Blob source by reference: same blob no reload, new blob reloads', () => {
    const blobA = new Blob(['a'], { type: 'audio/wav' });
    const { rerender } = render(<RichAudioPlayer source={blobA} />);
    const after1 = totalLoads();
    rerender(<RichAudioPlayer source={blobA} />);
    expect(totalLoads()).toBe(after1);
    rerender(<RichAudioPlayer source={new Blob(['b'], { type: 'audio/wav' })} />);
    expect(totalLoads()).toBeGreaterThan(after1);
  });
});
