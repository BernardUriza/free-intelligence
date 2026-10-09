// @vitest-environment jsdom
import { describe, it, expect, vi, beforeAll, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react';
import type { ConversationSummary } from '@free-intelligence/core';
import { ConversationArchiveDialog } from './ConversationArchiveDialog';

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.setAttribute('open', '');
  };
  HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
    this.removeAttribute('open');
  };
});
afterEach(cleanup);

const NOW = '2026-10-09T12:00:00.000Z';
const chat = (id: string, pinnedAt?: string): ConversationSummary => ({
  id,
  title: `Chat ${id}`,
  createdAt: NOW,
  updatedAt: NOW,
  preview: '',
  ...(pinnedAt ? { pinnedAt } : {}),
});
const chats = [chat('a'), chat('b'), chat('fijado', NOW)];
const box = (title: string) =>
  screen.getByText(title).closest('label')!.querySelector('input') as HTMLInputElement;

describe('<ConversationArchiveDialog>', () => {
  it('opens as a modal with every chat but the pinned one selected', () => {
    render(<ConversationArchiveDialog open conversations={chats} onArchive={vi.fn()} onClose={vi.fn()} />);
    expect(document.querySelector('dialog')!.hasAttribute('open')).toBe(true);
    expect(box('Chat a').checked).toBe(true);
    expect(box('Chat b').checked).toBe(true);
    expect(box('Chat fijado').checked).toBe(false);
    expect(screen.getByRole('button', { name: 'Archivar 2 chats' })).toBeTruthy();
  });

  it('selects all, archives the selection and closes on full success', async () => {
    const onArchive = vi.fn(async () => []);
    const onClose = vi.fn();
    render(<ConversationArchiveDialog open conversations={chats} onArchive={onArchive} onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: 'Seleccionar todos' }));
    fireEvent.click(screen.getByRole('button', { name: 'Archivar 3 chats' }));
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(onArchive).toHaveBeenCalledWith(['a', 'b', 'fijado']);
  });

  it('on a partial failure stays open with only the failed chats selected', async () => {
    const onArchive = vi.fn(async () => ['b']);
    const onClose = vi.fn();
    render(<ConversationArchiveDialog open conversations={chats} onArchive={onArchive} onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: 'Archivar 2 chats' }));
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('1 de 2'));
    expect(onClose).not.toHaveBeenCalled();
    expect(box('Chat a').checked).toBe(false);
    expect(box('Chat b').checked).toBe(true);
  });

  it('closes on Escape and never archives with nothing selected', () => {
    const onArchive = vi.fn(async () => []);
    const onClose = vi.fn();
    render(
      <ConversationArchiveDialog open conversations={[chat('x', NOW)]} onArchive={onArchive} onClose={onClose} />,
    );
    expect((screen.getByRole('button', { name: 'Archivar 0 chats' }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent(document.querySelector('dialog')!, new Event('cancel', { cancelable: true }));
    expect(onClose).toHaveBeenCalled();
    expect(onArchive).not.toHaveBeenCalled();
  });
});
