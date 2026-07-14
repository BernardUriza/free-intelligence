// @vitest-environment jsdom
/**
 * Tests for the sidebar/resource item primitives (B3-FIGLASS-SHELL-PRIMITIVES-1A).
 *
 * Pins the anatomy og118 hand-wrote twice: selectable row (keyboard + hover-safe),
 * hover/touch-revealed actions that don't bubble to select, and the inline-rename
 * contract from #283 — Enter commits, Escape cancels, blur commits, and crucially
 * Escape's unmount blur must NOT re-commit the discarded draft.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import {
  AgentSidebarItem,
  EditableResourceItem,
  ItemActionSlot,
  DestructiveActionSlot,
} from './AgentSidebarItem';

afterEach(cleanup);

describe('AgentSidebarItem', () => {
  it('renders a string title in the title slot and reflects selection', () => {
    render(<AgentSidebarItem selected onSelect={vi.fn()} title="Geografía MX" />);
    const row = screen.getByRole('button', { name: /Geografía MX/ }) as HTMLElement;
    expect(screen.getByText('Geografía MX')).toBeTruthy();
    expect(row.className).toContain('is-selected');
    expect(row.getAttribute('aria-current')).toBe('true');
  });

  it('selects on click and on Enter/Space when interactive', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<AgentSidebarItem selected={false} onSelect={onSelect} title="t" />);
    const row = screen.getByRole('button');
    await user.click(row);
    row.focus();
    await user.keyboard('{Enter}');
    await user.keyboard(' ');
    expect(onSelect).toHaveBeenCalledTimes(3);
  });

  it('does NOT select when selected, disabled, or editing', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const { rerender } = render(
      <AgentSidebarItem selected onSelect={onSelect} title="t" />,
    );
    await user.click(screen.getByRole('button'));
    rerender(<AgentSidebarItem selected={false} disabled onSelect={onSelect} title="t" />);
    await user.click(screen.getByRole('button'));
    rerender(<AgentSidebarItem selected={false} editing onSelect={onSelect} title="t" />);
    await user.click(screen.getByRole('button'));
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('fires onSelect on a selected row when toggleable (active-project deselect)', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<AgentSidebarItem selected toggleable onSelect={onSelect} title="t" />);
    const row = screen.getByRole('button');
    await user.click(row);
    row.focus();
    await user.keyboard('{Enter}');
    expect(onSelect).toHaveBeenCalledTimes(2);
  });

  it('renders subtitle and meta only when present', () => {
    const { rerender } = render(
      <AgentSidebarItem selected={false} onSelect={vi.fn()} title="t" subtitle="hola" meta="12:00" />,
    );
    expect(screen.getByText('hola')).toBeTruthy();
    expect(screen.getByText('12:00')).toBeTruthy();
    rerender(<AgentSidebarItem selected={false} onSelect={vi.fn()} title="t" subtitle="" />);
    expect(screen.queryByText('hola')).toBeNull();
  });
});

describe('ItemActionSlot / DestructiveActionSlot', () => {
  it('fires onActivate without bubbling to the row select', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const onActivate = vi.fn();
    render(
      <AgentSidebarItem
        selected={false}
        onSelect={onSelect}
        title="t"
        actions={<ItemActionSlot label="Act" onActivate={onActivate}>x</ItemActionSlot>}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'Act' }));
    expect(onActivate).toHaveBeenCalledTimes(1);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('respects disabled and tags the danger variant', () => {
    const onActivate = vi.fn();
    render(
      <DestructiveActionSlot label="Borrar" disabled onActivate={onActivate}>
        ×
      </DestructiveActionSlot>,
    );
    const btn = screen.getByRole('button', { name: 'Borrar' });
    expect(btn.className).toContain('fi-item-action--danger');
    expect((btn as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(btn);
    expect(onActivate).not.toHaveBeenCalled();
  });
});

function RenameHarness({
  initial = 'Geografía MX',
  onRename,
  emptyPolicy,
}: {
  initial?: string;
  onRename: (next: string) => void;
  emptyPolicy?: 'revert' | 'keep';
}) {
  const [title, setTitle] = useState(initial);
  return (
    <EditableResourceItem
      title={title}
      selected={false}
      onSelect={vi.fn()}
      onRename={(next) => {
        onRename(next);
        if (next.trim() !== '') setTitle(next);
      }}
      emptyPolicy={emptyPolicy}
      renameLabel="Renombrar"
      renameInputLabel="Nombre"
    />
  );
}

describe('EditableResourceItem — inline rename contract', () => {
  it('opens the editor and commits the new title on Enter', async () => {
    const user = userEvent.setup();
    const onRename = vi.fn();
    render(<RenameHarness onRename={onRename} />);
    await user.click(screen.getByRole('button', { name: 'Renombrar' }));
    const input = screen.getByRole('textbox', { name: 'Nombre' });
    await user.clear(input);
    await user.type(input, 'Mundial 2026{Enter}');
    expect(onRename).toHaveBeenCalledWith('Mundial 2026');
    expect(screen.queryByRole('textbox')).toBeNull();
  });

  it('commits on blur', async () => {
    const user = userEvent.setup();
    const onRename = vi.fn();
    render(<RenameHarness onRename={onRename} />);
    await user.click(screen.getByRole('button', { name: 'Renombrar' }));
    const input = screen.getByRole('textbox', { name: 'Nombre' });
    await user.clear(input);
    await user.type(input, 'Por blur');
    fireEvent.blur(input);
    expect(onRename).toHaveBeenCalledWith('Por blur');
  });

  it('Escape cancels — and the ensuing blur does NOT re-commit the discarded draft', async () => {
    const user = userEvent.setup();
    const onRename = vi.fn();
    render(<RenameHarness onRename={onRename} />);
    await user.click(screen.getByRole('button', { name: 'Renombrar' }));
    const input = screen.getByRole('textbox', { name: 'Nombre' });
    await user.clear(input);
    await user.type(input, 'descartar');
    fireEvent.keyDown(input, { key: 'Escape' });
    fireEvent.blur(input);
    expect(onRename).not.toHaveBeenCalled();
    expect(screen.queryByRole('textbox')).toBeNull();
    expect(screen.getByText('Geografía MX')).toBeTruthy();
  });

  it('empty draft reverts (default policy) by calling onRename("")', async () => {
    const user = userEvent.setup();
    const onRename = vi.fn();
    render(<RenameHarness onRename={onRename} />);
    await user.click(screen.getByRole('button', { name: 'Renombrar' }));
    const input = screen.getByRole('textbox', { name: 'Nombre' });
    await user.clear(input);
    await user.keyboard('{Enter}');
    expect(onRename).toHaveBeenCalledWith('');
  });

  it('empty draft with keep policy cancels silently (no onRename)', async () => {
    const user = userEvent.setup();
    const onRename = vi.fn();
    render(<RenameHarness onRename={onRename} emptyPolicy="keep" />);
    await user.click(screen.getByRole('button', { name: 'Renombrar' }));
    const input = screen.getByRole('textbox', { name: 'Nombre' });
    await user.clear(input);
    await user.keyboard('{Enter}');
    expect(onRename).not.toHaveBeenCalled();
  });

  it('the rename trigger is hidden while editing', async () => {
    const user = userEvent.setup();
    render(<RenameHarness onRename={vi.fn()} />);
    await user.click(screen.getByRole('button', { name: 'Renombrar' }));
    expect(screen.queryByRole('button', { name: 'Renombrar' })).toBeNull();
  });
});
