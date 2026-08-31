// @vitest-environment jsdom
/**
 * The two rules that are not decoration.
 *
 * A list of reasons is ordered on purpose by whoever built it — the entry that
 * changes a decision goes first — so the component must never reorder it. And a
 * titled box with nothing in it reads as a system with an opinion it will not
 * say, so empty renders nothing at all.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { Callout, CalloutList } from './Callout';

afterEach(cleanup);

describe('CalloutList', () => {
  it('renders nothing when there is nothing to say', () => {
    const { container } = render(<CalloutList title="Faltan campos" items={[]} tone="danger" />);
    expect(container.firstChild).toBeNull();
  });

  it('keeps the caller order — the first entry stays first', () => {
    render(
      <CalloutList
        title="Advertencias"
        tone="warning"
        items={['no se imprimirá', 'interacción', 'dosis']}
      />,
    );
    const textos = Array.from(document.querySelectorAll('li')).map((li) => li.textContent);
    expect(textos).toEqual(['no se imprimirá', 'interacción', 'dosis']);
  });

  it('preserves the newlines inside one entry instead of running it together', () => {
    render(<CalloutList items={['primera línea\nsegunda línea']} />);
    expect(document.querySelector('li')?.textContent).toBe('primera línea\nsegunda línea');
  });
});

describe('Callout', () => {
  it('announces a danger the moment it appears', () => {
    render(<Callout tone="danger">algo salió mal</Callout>);
    expect(screen.getByRole('alert').textContent).toContain('algo salió mal');
  });

  it('does not shout a neutral note', () => {
    render(<Callout>una nota</Callout>);
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('lets the caller override the announcement either way', () => {
    const { rerender } = render(<Callout tone="warning" live>ojo</Callout>);
    expect(screen.getByRole('alert')).toBeTruthy();
    rerender(<Callout tone="danger" live={false}>callado</Callout>);
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
