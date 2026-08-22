// @vitest-environment jsdom
/**
 * The index grid and its card (FIGLASS-PROJECTS-PAGE-1).
 *
 * Pins the two things a consumer cannot re-decide: the list is a semantic ul/li
 * (so a screen reader can count and traverse it), and a card with an `href` is a
 * REAL anchor — middle-clickable, new-tab-able — not a div with an onClick.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ResourceCard, ResourceCardGrid } from './ResourceCardGrid';

afterEach(cleanup);

describe('ResourceCardGrid', () => {
  it('renders one list item per child under a named list', () => {
    render(
      <ResourceCardGrid ariaLabel="Recursos">
        {[<ResourceCard key="a" title="Uno" />, <ResourceCard key="b" title="Dos" />]}
      </ResourceCardGrid>,
    );

    const list = screen.getByRole('list', { name: 'Recursos' });
    expect(list.tagName).toBe('UL');
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
  });

  it('shows the empty state INSTEAD of an empty grid', () => {
    render(
      <ResourceCardGrid ariaLabel="Recursos" emptyState={<p>Nada todavía</p>}>
        {[]}
      </ResourceCardGrid>,
    );

    expect(screen.getByText('Nada todavía')).toBeTruthy();
    expect(screen.queryByRole('list')).toBeNull();
  });

  it('still renders the grid with no children when no empty state was supplied', () => {
    render(<ResourceCardGrid ariaLabel="Recursos">{[]}</ResourceCardGrid>);

    expect(screen.getByRole('list', { name: 'Recursos' })).toBeTruthy();
  });
});

describe('ResourceCard', () => {
  it('is a real anchor when given an href', () => {
    render(<ResourceCard title="Uno" href="/r/uno" />);

    const link = screen.getByRole('link', { name: /Uno/ });
    expect(link.getAttribute('href')).toBe('/r/uno');
  });

  it('is a button when given no href', async () => {
    const onClick = vi.fn();
    render(<ResourceCard title="Uno" onClick={onClick} />);

    await userEvent.click(screen.getByRole('button', { name: /Uno/ }));

    expect(onClick).toHaveBeenCalledOnce();
    expect(screen.queryByRole('link')).toBeNull();
  });

  it('omits the description and meta rows entirely when absent', () => {
    const { container } = render(<ResourceCard title="Uno" />);

    expect(container.querySelector('.fi-resource-card-desc')).toBeNull();
    expect(container.querySelector('.fi-resource-card-meta')).toBeNull();
  });

  it('renders an already-formatted meta as given — fi-glass does no relative time', () => {
    render(<ResourceCard title="Uno" description="algo" meta="Updated 6 days ago" />);

    expect(screen.getByText('Updated 6 days ago')).toBeTruthy();
    expect(screen.getByText('algo')).toBeTruthy();
  });

  it('carries the framework touch minimum', () => {
    const { container } = render(<ResourceCard title="Uno" />);

    expect(container.querySelector('.fi-touch-target')).not.toBeNull();
  });
});
