// @vitest-environment jsdom
/**
 * The index search box and its matching rule (FIGLASS-PROJECTS-PAGE-1).
 *
 * The rule that earns its own test is accent folding: typing "papeleria" must
 * find "Papelería". A Spanish-speaking user on a phone keyboard routinely omits
 * the accent, and a naive `includes` would answer "no results" to a query that
 * is obviously right.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ResourceSearchInput, filterByQuery } from './ResourceSearchInput';

afterEach(cleanup);

describe('ResourceSearchInput', () => {
  it('is controlled and reports every keystroke', async () => {
    const onChange = vi.fn();
    render(<ResourceSearchInput value="" onChange={onChange} ariaLabel="Buscar" />);

    await userEvent.type(screen.getByRole('searchbox', { name: 'Buscar' }), 'pa');

    expect(onChange).toHaveBeenCalledTimes(2);
  });
});

describe('filterByQuery', () => {
  const items = [
    { name: 'Papelería', description: 'precios y proveedores' },
    { name: 'Contabilidad', description: 'SAT' },
  ];
  const fields = (i: (typeof items)[number]) => [i.name, i.description];

  it('finds an accented name from an unaccented query', () => {
    expect(filterByQuery(items, 'papeleria', fields)).toHaveLength(1);
  });

  it('ignores case', () => {
    expect(filterByQuery(items, 'PAPELERÍA', fields)).toHaveLength(1);
  });

  it('matches on any field the consumer names, not just the first', () => {
    expect(filterByQuery(items, 'proveedores', fields)[0].name).toBe('Papelería');
  });

  it('an empty or whitespace query matches everything, not nothing', () => {
    expect(filterByQuery(items, '', fields)).toHaveLength(2);
    expect(filterByQuery(items, '   ', fields)).toHaveLength(2);
  });

  it('tolerates an undefined field instead of throwing', () => {
    const sparse = [{ name: 'Uno', description: undefined }];
    expect(filterByQuery(sparse, 'uno', (i) => [i.name, i.description])).toHaveLength(1);
  });

  it('returns nothing when nothing matches', () => {
    expect(filterByQuery(items, 'zzz', fields)).toHaveLength(0);
  });
});
