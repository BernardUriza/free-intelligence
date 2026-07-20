/**
 * Tests for RichAudioPlayer — formatting helper + the control surface.
 *
 * The transport/seek behavior is covered at the engine level
 * (createAudioPlayer.test.ts). Here we lock the pure mm:ss formatter and assert
 * the rich surface renders all controls with the right a11y wiring and starts
 * fully disabled when there is no source. Static SSR markup suffices: the engine
 * only constructs an Audio element on load(), which SSR never reaches.
 */

import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { RichAudioPlayer, formatPlaybackTime } from './RichAudioPlayer';

describe('formatPlaybackTime', () => {
  it('formats seconds as mm:ss', () => {
    expect(formatPlaybackTime(0)).toBe('0:00');
    expect(formatPlaybackTime(5)).toBe('0:05');
    expect(formatPlaybackTime(65)).toBe('1:05');
    expect(formatPlaybackTime(600)).toBe('10:00');
  });
  it('grows to h:mm:ss past an hour', () => {
    expect(formatPlaybackTime(3661)).toBe('1:01:01');
  });
  it('collapses NaN/negative (pre-metadata duration) to 0:00', () => {
    expect(formatPlaybackTime(NaN)).toBe('0:00');
    expect(formatPlaybackTime(-10)).toBe('0:00');
  });
});

describe('<RichAudioPlayer> control surface', () => {
  it('renders skip/play/stop/skip + a progress scrubber', () => {
    const html = renderToStaticMarkup(<RichAudioPlayer />);
    expect(html).toContain('aria-label="Retroceder 10 segundos"');
    expect(html).toContain('aria-label="Reproducir audio"');
    expect(html).toContain('aria-label="Detener audio"');
    expect(html).toContain('aria-label="Avanzar 10 segundos"');
    expect(html).toContain('aria-label="Progreso de reproducción"');
    expect(html).toContain('data-fi-audio-player="rich"');
  });

  it('honors a custom skipSeconds in the control labels', () => {
    const html = renderToStaticMarkup(<RichAudioPlayer skipSeconds={5} />);
    expect(html).toContain('aria-label="Retroceder 5 segundos"');
    expect(html).toContain('aria-label="Avanzar 5 segundos"');
  });

  it('starts disabled and at 0:00 / 0:00 when there is no source', () => {
    const html = renderToStaticMarkup(<RichAudioPlayer />);
    expect(html).toContain('disabled');
    expect(html).toContain('0:00 / 0:00');
  });

  it('can hide the time readout', () => {
    const html = renderToStaticMarkup(<RichAudioPlayer showTime={false} />);
    expect(html).not.toContain('data-fi-audio-time');
  });
});

describe('<RichAudioPlayer> compact transport (mobile composer)', () => {
  it('keeps only play/pause + scrubber, dropping skip and stop', () => {
    const html = renderToStaticMarkup(<RichAudioPlayer compact />);
    expect(html).toContain('aria-label="Reproducir audio"');
    expect(html).toContain('aria-label="Progreso de reproducción"');
    expect(html).not.toContain('aria-label="Retroceder 10 segundos"');
    expect(html).not.toContain('aria-label="Avanzar 10 segundos"');
    expect(html).not.toContain('aria-label="Detener audio"');
  });

  it('renders a SINGLE visible time readout (not the dual mm:ss / mm:ss)', () => {
    const html = renderToStaticMarkup(<RichAudioPlayer compact />);
    expect(html).toContain('data-fi-audio-time');
    // The VISIBLE span shows one value (clip length 0:00 when idle); the dual
    // "0:00 / 0:00" survives only in the scrubber's aria-valuetext for a11y.
    expect(html).toContain('>0:00</span>');
    expect(html).not.toContain('>0:00 / 0:00</span>');
  });
});
