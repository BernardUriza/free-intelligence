// @vitest-environment jsdom
/**
 * The rail's stacked panels (FIGLASS-PROJECTS-PAGE-1).
 *
 * Dividers come from a CSS adjacency rule, never from a prop: the first panel is
 * not asked to know it is first, so a consumer cannot draw a stray line at the
 * top of the stack by reordering its children.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { RailPanel, RailPanelStack } from './RailPanel';

afterEach(cleanup);

describe('RailPanel', () => {
  it('renders a string title in the title slot and keeps the action beside it', () => {
    const { container } = render(
      <RailPanel title="Context" actionSlot={<button type="button">Add</button>}>
        body
      </RailPanel>,
    );

    expect(container.querySelector('.fi-rail-panel-title')?.textContent).toBe('Context');
    expect(screen.getByRole('button', { name: 'Add' })).toBeTruthy();
    expect(screen.getByText('body')).toBeTruthy();
  });

  it('uses a node title as-is, without wrapping it', () => {
    const { container } = render(<RailPanel title={<h3>Memory</h3>}>body</RailPanel>);

    expect(container.querySelector('.fi-rail-panel-title')).toBeNull();
    expect(screen.getByRole('heading', { name: 'Memory' })).toBeTruthy();
  });

  it('renders a head-only panel with no body', () => {
    render(<RailPanel title="Scheduled" />);

    expect(screen.getByText('Scheduled')).toBeTruthy();
  });

  it('takes no divider prop — the stack decides adjacency in CSS', () => {
    const { container } = render(
      <RailPanelStack>
        <RailPanel title="Uno">a</RailPanel>
        <RailPanel title="Dos">b</RailPanel>
      </RailPanelStack>,
    );

    expect(container.querySelectorAll('.fi-rail-panel')).toHaveLength(2);
    expect(container.querySelector('.fi-rail-stack')).not.toBeNull();
  });
});
