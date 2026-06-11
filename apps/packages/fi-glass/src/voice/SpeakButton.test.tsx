/**
 * Tests for SpeakButton busy state (B3-VOICE-FIGLASS-6).
 *
 * TTS synthesis takes seconds; a silent button reads as dead and invites paid
 * spam clicks. `busy` renders a spinner, disables the button and sets aria-busy.
 * SSR markup pins the contract; the click-guard is in the disabled attribute.
 */

import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { SpeakButton } from './SpeakButton';

describe('<SpeakButton> busy (B3-VOICE-FIGLASS-6)', () => {
  it('renders enabled with the speaker icon by default (backward-compatible)', () => {
    const html = renderToStaticMarkup(
      <SpeakButton content="hola" onOpenPlayer={() => {}} />,
    );
    expect(html).not.toContain('disabled');
    expect(html).not.toContain('aria-busy="true"');
    expect(html).toContain('Escuchar (Nova)');
  });

  it('renders disabled with spinner + aria-busy while busy', () => {
    const html = renderToStaticMarkup(
      <SpeakButton content="hola" onOpenPlayer={() => {}} busy />,
    );
    expect(html).toContain('disabled');
    expect(html).toContain('aria-busy="true"');
    expect(html).toContain('animate-spin');
    expect(html).toContain('Generando audio…');
  });

  it('uses a custom busyTitle when provided', () => {
    const html = renderToStaticMarkup(
      <SpeakButton content="hola" onOpenPlayer={() => {}} busy busyTitle="Sintetizando…" />,
    );
    expect(html).toContain('Sintetizando…');
  });
});

describe('<SpeakButton> cached (B3-VOICE-FIGLASS-8)', () => {
  it('renders the Play affordance, enabled, when the clip is cached', () => {
    const html = renderToStaticMarkup(
      <SpeakButton content="hola" onOpenPlayer={() => {}} cached />,
    );
    expect(html).toContain('Reproducir (ya generado)');
    expect(html).not.toContain('disabled');
    // The speaker tooltip is replaced — this is the "instant + free" affordance.
    expect(html).not.toContain('Escuchar (Nova)');
  });

  it('busy takes precedence over cached (spinner while re-synthesizing)', () => {
    const html = renderToStaticMarkup(
      <SpeakButton content="hola" onOpenPlayer={() => {}} cached busy />,
    );
    expect(html).toContain('animate-spin');
    expect(html).toContain('Generando audio…');
    expect(html).not.toContain('Reproducir (ya generado)');
  });

  it('uses a custom cachedTitle when provided', () => {
    const html = renderToStaticMarkup(
      <SpeakButton content="hola" onOpenPlayer={() => {}} cached cachedTitle="Replay gratis" />,
    );
    expect(html).toContain('Replay gratis');
  });
});
