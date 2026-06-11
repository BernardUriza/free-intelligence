/**
 * Tests for normalizeStreamedMarkdown (B3-FIGLASS-9) — the chunk-boundary glue
 * repair. Pins the audit case (`fin.## Título` renders as a heading) and, just
 * as important, the false-positive guards: inline `#` usage and fenced code are
 * never rewritten.
 */

import { describe, it, expect } from 'vitest';
import { normalizeStreamedMarkdown } from './normalizeStreamedMarkdown';

describe('normalizeStreamedMarkdown', () => {
  it('repairs a heading glued onto sentence punctuation (the audit case)', () => {
    expect(
      normalizeStreamedMarkdown('cargar las herramientas necesarias.## Respuesta sobre THC'),
    ).toBe('cargar las herramientas necesarias.\n\n## Respuesta sobre THC');
  });

  it('repairs all heading levels and multiple occurrences', () => {
    expect(normalizeStreamedMarkdown('uno.# H1 dos.### H3')).toBe(
      'uno.\n\n# H1 dos.\n\n### H3',
    );
  });

  it('repairs glue after other sentence punctuation (?, !, :, closing quote)', () => {
    expect(normalizeStreamedMarkdown('¿listo?## Sí')).toBe('¿listo?\n\n## Sí');
    expect(normalizeStreamedMarkdown('"fin"## Título')).toBe('"fin"\n\n## Título');
  });

  it('leaves a well-formed heading untouched', () => {
    expect(normalizeStreamedMarkdown('## Título')).toBe('## Título');
    expect(normalizeStreamedMarkdown('texto.\n\n## Título')).toBe('texto.\n\n## Título');
  });

  it('leaves lists, paragraphs and plain text intact', () => {
    const md = 'Párrafo normal.\n\n- uno\n- dos\n\n1. primero\n2. segundo';
    expect(normalizeStreamedMarkdown(md)).toBe(md);
    expect(normalizeStreamedMarkdown('sin markdown aquí')).toBe('sin markdown aquí');
  });

  it('never touches inline # usage (C#, issue numbers, "the # key")', () => {
    expect(normalizeStreamedMarkdown('C# is nice')).toBe('C# is nice');
    expect(normalizeStreamedMarkdown('ver issue #123.')).toBe('ver issue #123.');
    expect(normalizeStreamedMarkdown('usa la tecla # para continuar')).toBe(
      'usa la tecla # para continuar',
    );
  });

  it('never rewrites inside fenced code blocks', () => {
    const md = 'antes.\n```js\nconst x = 1;.## not a heading\n```\ndespués.## Título';
    expect(normalizeStreamedMarkdown(md)).toBe(
      'antes.\n```js\nconst x = 1;.## not a heading\n```\ndespués.\n\n## Título',
    );
  });

  it('treats an unterminated fence (mid-stream) as code to the end', () => {
    const md = 'texto.\n```python\nprint("x").## glued in code';
    expect(normalizeStreamedMarkdown(md)).toBe(md);
  });
});
