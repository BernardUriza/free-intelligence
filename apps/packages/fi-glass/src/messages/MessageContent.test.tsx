/**
 * Tests for MessageContent markdown rendering (B3-FIGLASS-9).
 *
 * The audit case end-to-end at the component level: a heading the stream glued
 * onto the previous sentence must render as a real <h2>, not as literal "##"
 * paragraph text. SSR markup is enough — react-markdown renders synchronously.
 */

import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MessageContent } from './MessageContent';

describe('<MessageContent> markdown headings', () => {
  it('renders a well-formed heading as a heading element', () => {
    const html = renderToStaticMarkup(
      <MessageContent isUser={false} content={'## Respuesta'} />,
    );
    expect(html).toContain('<h2');
    expect(html).toContain('Respuesta');
  });

  it('renders a stream-glued heading as a heading, not literal ## text (audit case)', () => {
    const html = renderToStaticMarkup(
      <MessageContent
        isUser={false}
        content={'cargar las herramientas necesarias.## Respuesta sobre el consumo'}
      />,
    );
    expect(html).toContain('<h2');
    expect(html).toContain('Respuesta sobre el consumo');
    expect(html).not.toContain('##');
  });

  it('keeps lists and paragraphs intact through normalization', () => {
    const html = renderToStaticMarkup(
      <MessageContent
        isUser={false}
        content={'Intro.\n\n- uno\n- dos\n\nPárrafo final.'}
      />,
    );
    expect(html).toContain('<ul');
    expect((html.match(/<li/g) ?? []).length).toBe(2);
    expect(html).toContain('Párrafo final.');
  });

  it('does not promote glued ## inside code fences', () => {
    const html = renderToStaticMarkup(
      <MessageContent
        isUser={false}
        content={'mira:\n```\nfoo.## bar\n```'}
      />,
    );
    expect(html).toContain('<pre');
    expect(html).toContain('foo.## bar');
    expect(html).not.toContain('<h2');
  });

  it('user messages stay plain text (no markdown parsing at all)', () => {
    const html = renderToStaticMarkup(
      <MessageContent isUser={true} content={'fin.## esto no es heading'} />,
    );
    expect(html).not.toContain('<h2');
    expect(html).toContain('fin.## esto no es heading');
  });
});
