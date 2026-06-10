/**
 * Tests for ComposerMicSlot — the reusable mic affordance.
 *
 * The slot must render the right disabled/unavailable state WITHOUT an STT
 * backend, and become an enabled record/stop toggle only when the consumer
 * declares capability. Static SSR markup is enough to assert the disabled state,
 * aria-labels, and the icon/role transitions — no jsdom, no recorder.
 */

import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { ComposerMicSlot } from './ComposerMicSlot';

describe('<ComposerMicSlot> unavailable (default)', () => {
  it('renders a disabled button with the unavailable label', () => {
    const html = renderToStaticMarkup(<ComposerMicSlot />);
    expect(html).toContain('disabled');
    expect(html).toContain('aria-disabled="true"');
    expect(html).toContain('Dictado por voz no disponible todavía');
    expect(html).toContain('data-fi-mic-slot');
    // unavailable slot does not advertise the available flag
    expect(html).not.toContain('data-available=""');
  });

  it('uses a custom unavailable label when provided', () => {
    const html = renderToStaticMarkup(
      <ComposerMicSlot unavailableLabel="STT llega pronto" />
    );
    expect(html).toContain('STT llega pronto');
  });
});

describe('<ComposerMicSlot> available', () => {
  it('renders an enabled start affordance when idle', () => {
    const html = renderToStaticMarkup(<ComposerMicSlot available />);
    expect(html).toContain('aria-label="Iniciar dictado por voz"');
    expect(html).toContain('aria-disabled="false"');
    expect(html).toContain('data-available=""');
    expect(html).not.toContain('disabled=""');
  });

  it('reflects recording state with aria-pressed and a stop label', () => {
    const html = renderToStaticMarkup(<ComposerMicSlot available recording />);
    expect(html).toContain('aria-pressed="true"');
    expect(html).toContain('aria-label="Detener dictado por voz"');
  });

  it('disables and announces while busy/transcribing', () => {
    const html = renderToStaticMarkup(<ComposerMicSlot available busy />);
    expect(html).toContain('aria-disabled="true"');
    expect(html).toContain('Transcribiendo');
  });
});
