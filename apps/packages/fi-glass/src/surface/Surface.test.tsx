// @vitest-environment jsdom
/**
 * The rules that are not decoration.
 *
 * A DataTable's rows are ordered on purpose by whoever built them, so the
 * component never reorders; and an empty table renders nothing at all, same
 * doctrine as CalloutList. A Literal is verbatim: whitespace survives. And
 * `live` is opt-in — a static literal must not narrate itself.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { DataTable, Literal, Note, Panel } from './Surface';

afterEach(cleanup);

describe('Panel', () => {
  it('renders the title as a heading only when given', () => {
    render(<Panel title="Motor">contenido</Panel>);
    expect(screen.getByRole('heading', { name: 'Motor' })).toBeTruthy();
    const { container } = render(<Panel>solo</Panel>);
    expect(container.querySelector('h2')).toBeNull();
  });
});

describe('Literal', () => {
  it('is verbatim and silent by default, live only on request', () => {
    const { container } = render(<Literal>{'línea 1\n  sangrada'}</Literal>);
    const pre = container.querySelector('pre');
    expect(pre?.textContent).toBe('línea 1\n  sangrada');
    expect(pre?.getAttribute('aria-live')).toBeNull();
    const viva = render(<Literal live>fragmento</Literal>);
    expect(viva.container.querySelector('pre')?.getAttribute('aria-live')).toBe('polite');
  });

  it('quotes mid-sentence as a span when inline', () => {
    const { container } = render(<Literal inline>{'fiebre > 38.5'}</Literal>);
    expect(container.querySelector('pre')).toBeNull();
    expect(container.querySelector('span')?.textContent).toBe('fiebre > 38.5');
  });
});

describe('Note', () => {
  it('renders a paragraph', () => {
    const { container } = render(<Note>al margen</Note>);
    expect(container.querySelector('p')?.textContent).toBe('al margen');
  });

  it('renders a span when inline — a note inside a sentence must not break it', () => {
    const { container } = render(<Note inline>(p. 12)</Note>);
    expect(container.querySelector('p')).toBeNull();
    expect(container.querySelector('span')?.textContent).toBe('(p. 12)');
  });
});

describe('DataTable', () => {
  it('renders nothing when there are no rows', () => {
    const { container } = render(<DataTable head={['A']} rows={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('keeps the caller order — the first row stays first', () => {
    render(
      <DataTable
        head={['Clave', 'Título']}
        rows={[
          { key: 'b', cells: ['B-2', 'segunda escrita primero' ] },
          { key: 'a', cells: ['A-1', 'primera escrita después'] },
        ]}
      />,
    );
    const filas = Array.from(document.querySelectorAll('tbody tr td:first-child')).map(
      (td) => td.textContent,
    );
    expect(filas).toEqual(['B-2', 'A-1']);
  });

  it('renders the first cell as a row header when asked', () => {
    render(<DataTable rowHeader rows={[{ key: 'x', cells: ['Local', 'listo'] }]} />);
    const th = document.querySelector('tbody th');
    expect(th?.getAttribute('scope')).toBe('row');
    expect(th?.textContent).toBe('Local');
  });
});
