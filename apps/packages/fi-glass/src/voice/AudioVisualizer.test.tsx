/**
 * Tests for AudioVisualizer + its pure helpers.
 *
 * The visualizer is intentionally data-driven and effect-free so it renders the
 * same DOM for the same props with no microphone, AudioContext, or network.
 * That lets us assert structure with static SSR markup (no jsdom) and unit-test
 * the clamping/resampling rules directly.
 */

import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import {
  AudioVisualizer,
  normalizeLevels,
  resampleLevels,
} from './AudioVisualizer';

const countBars = (html: string) =>
  (html.match(/data-fi-audio-bar/g) ?? []).length;

describe('normalizeLevels', () => {
  it('clamps to [0,1] and zeroes non-finite values', () => {
    expect(normalizeLevels([-1, 0, 0.5, 1, 2, NaN, Infinity])).toEqual([
      0, 0, 0.5, 1, 1, 0, 0,
    ]);
  });
});

describe('resampleLevels', () => {
  it('returns the same array when count matches', () => {
    expect(resampleLevels([0.1, 0.2, 0.3], 3)).toEqual([0.1, 0.2, 0.3]);
  });
  it('down/up-samples to the requested count', () => {
    expect(resampleLevels([0, 1], 4)).toHaveLength(4);
    expect(resampleLevels([0, 0.5, 1, 0.5], 2)).toHaveLength(2);
  });
  it('pads with zeros when given no levels', () => {
    expect(resampleLevels([], 3)).toEqual([0, 0, 0]);
  });
  it('returns empty for non-positive count', () => {
    expect(resampleLevels([0.5], 0)).toEqual([]);
  });
});

describe('<AudioVisualizer> bars', () => {
  it('renders one bar per injected level', () => {
    const html = renderToStaticMarkup(
      <AudioVisualizer levels={[0.2, 0.4, 0.6, 0.8]} />
    );
    expect(countBars(html)).toBe(4);
    expect(html).toContain('data-fi-audio-visualizer="bars"');
  });

  it('honors a fixed barCount by resampling', () => {
    const html = renderToStaticMarkup(
      <AudioVisualizer levels={[0.1, 0.9]} barCount={6} />
    );
    expect(countBars(html)).toBe(6);
  });

  it('renders bars at rest when inactive', () => {
    const active = renderToStaticMarkup(
      <AudioVisualizer levels={[1, 1]} active />
    );
    const inactive = renderToStaticMarkup(
      <AudioVisualizer levels={[1, 1]} active={false} />
    );
    // Active full level -> 100% height; inactive collapses to the resting sliver.
    expect(active).toContain('height:100%');
    expect(inactive).not.toContain('height:100%');
  });

  it('exposes an accessible image role + label', () => {
    const html = renderToStaticMarkup(
      <AudioVisualizer levels={[0.5]} label="Niveles de voz" />
    );
    expect(html).toContain('role="img"');
    expect(html).toContain('aria-label="Niveles de voz"');
  });
});

describe('<AudioVisualizer> pulse', () => {
  it('renders a single pulse core scaled by the peak level', () => {
    const html = renderToStaticMarkup(
      <AudioVisualizer levels={[0.2, 1, 0.4]} variant="pulse" />
    );
    expect(html).toContain('data-fi-audio-visualizer="pulse"');
    expect(html).toContain('data-fi-pulse-core');
    expect(html).toContain('scale(2)'); // peak 1 -> 1 + 1
  });

  it('collapses to rest scale when inactive', () => {
    const html = renderToStaticMarkup(
      <AudioVisualizer levels={[1]} variant="pulse" active={false} />
    );
    expect(html).toContain('scale(1)');
  });
});
