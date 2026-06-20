/**
 * Tests for the B3-FIGLASS-MOBILE-2 touch-target primitive.
 *
 * jsdom cannot measure layout, so these assert the STRUCTURAL contract: the pure
 * helpers compose correctly, the SSR-safe injector never throws without a
 * document, and every fi-glass control that opts in renders the additive
 * `fi-touch-target` class WITHOUT dropping the consumer's own className. The real
 * 44×44 measurement is the live smoke at 390×844 — this guards the wiring.
 */

import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import {
  FI_TOUCH_TARGET_CLASS,
  ensureTouchTargetStyle,
  withTouchTarget,
} from './touchTarget';
import { SpeakButton } from '../voice/SpeakButton';
import { ComposerMicSlot } from '../voice/ComposerMicSlot';
import { CopyButton } from '../messages/CopyButton';
import { RichAudioPlayer } from '../voice/RichAudioPlayer';

describe('touch-target primitive', () => {
  it('exposes the stable class name', () => {
    expect(FI_TOUCH_TARGET_CLASS).toBe('fi-touch-target');
  });

  it('composes additively, preserving the consumer class', () => {
    expect(withTouchTarget()).toBe('fi-touch-target');
    expect(withTouchTarget('og-sidebar-new')).toBe('fi-touch-target og-sidebar-new');
  });

  it('ensureTouchTargetStyle is SSR-safe (no document → no throw)', () => {
    expect(() => ensureTouchTargetStyle()).not.toThrow();
  });
});

describe('fi-glass controls carry the touch-target minimum', () => {
  it('SpeakButton renders fi-touch-target', () => {
    const html = renderToStaticMarkup(
      <SpeakButton content="hola" onOpenPlayer={() => {}} />
    );
    expect(html).toContain('fi-touch-target');
  });

  it('SpeakButton keeps the consumer className alongside the minimum', () => {
    const html = renderToStaticMarkup(
      <SpeakButton content="hola" onOpenPlayer={() => {}} className="og-speak" />
    );
    expect(html).toContain('fi-touch-target');
    expect(html).toContain('og-speak');
  });

  it('ComposerMicSlot renders fi-touch-target', () => {
    const html = renderToStaticMarkup(<ComposerMicSlot available />);
    expect(html).toContain('fi-touch-target');
  });

  it('CopyButton renders fi-touch-target', () => {
    const html = renderToStaticMarkup(<CopyButton content="hola" />);
    expect(html).toContain('fi-touch-target');
  });

  it('RichAudioPlayer transport buttons render fi-touch-target', () => {
    const html = renderToStaticMarkup(<RichAudioPlayer source={null} />);
    expect(html).toContain('fi-touch-target');
  });
});
