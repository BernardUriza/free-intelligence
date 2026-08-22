// @vitest-environment jsdom
/**
 * The knowledge panel's document cards (FIGLASS-PROJECTS-PAGE-1).
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DocCard, DocCardGrid } from './DocCard';

afterEach(cleanup);

describe('DocCard', () => {
  it('renders title, meta and badge, and reports clicks', async () => {
    const onClick = vi.fn();
    render(<DocCard title="precios.md" meta="67 lines" badge="text" onClick={onClick} />);

    await userEvent.click(screen.getByRole('button', { name: /precios\.md/ }));

    expect(onClick).toHaveBeenCalledOnce();
    expect(screen.getByText('67 lines')).toBeTruthy();
    expect(screen.getByText('text')).toBeTruthy();
  });

  it('keeps the full name reachable as a title attribute even though it clamps', () => {
    render(<DocCard title="un-nombre-larguisimo-que-se-corta.md" />);

    expect(
      screen.getByRole('button').getAttribute('title'),
    ).toBe('un-nombre-larguisimo-que-se-corta.md');
  });

  it('omits badge and meta when absent', () => {
    const { container } = render(<DocCard title="a.md" />);

    expect(container.querySelector('.fi-doc-card-badge')).toBeNull();
    expect(container.querySelector('.fi-doc-card-meta')).toBeNull();
  });

  it('carries the framework touch minimum', () => {
    const { container } = render(<DocCard title="a.md" />);

    expect(container.querySelector('.fi-touch-target')).not.toBeNull();
  });
});

describe('DocCardGrid', () => {
  it('is a named ul with one li per document', () => {
    render(
      <DocCardGrid ariaLabel="Documentos">
        {[<DocCard key="a" title="a.md" />, <DocCard key="b" title="b.md" />]}
      </DocCardGrid>,
    );

    expect(screen.getByRole('list', { name: 'Documentos' }).tagName).toBe('UL');
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
  });

  it('swaps in the empty state for an empty corpus', () => {
    render(
      <DocCardGrid ariaLabel="Documentos" emptyState={<p>Sin documentos</p>}>
        {[]}
      </DocCardGrid>,
    );

    expect(screen.getByText('Sin documentos')).toBeTruthy();
    expect(screen.queryByRole('list')).toBeNull();
  });
});
