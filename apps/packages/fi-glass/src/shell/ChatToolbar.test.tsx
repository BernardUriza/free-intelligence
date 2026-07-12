// @vitest-environment jsdom
/**
 * aurity's toolbar menu is the SSOT of this framework's menu anatomy.
 *
 * It now RENDERS `ActionMenu` instead of hand-writing a second dropdown (og118's
 * composer had grown its own, incompatible one — the duplication was the bug).
 * These tests pin the extraction to the letter: same trigger, same items in the
 * same order, same classes, same dividers, same compact-only gates, same portal.
 * If the refactor changed one pixel of aurity's menu, it broke the SSOT.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, cleanup, fireEvent } from '@testing-library/react';
import { ChatToolbar } from './ChatToolbar';

const trigger = () =>
  document.querySelector('button[aria-label="Más opciones"]') as HTMLButtonElement;
const items = () => Array.from(document.querySelectorAll('[role="menuitem"]'));
const open = () => fireEvent.click(trigger());

afterEach(cleanup);

describe('<ChatToolbar> overflow menu (aurity, the SSOT)', () => {
  it('keeps the "⋮ Más opciones" trigger', () => {
    render(<ChatToolbar onAttach={vi.fn()} />);
    expect(trigger()).not.toBeNull();
  });

  it('keeps every entry, in order, with aurity\'s wording', () => {
    render(
      <ChatToolbar
        onAttach={vi.fn()}
        onLanguage={vi.fn()}
        onFormatting={vi.fn()}
        onCopyCurl={vi.fn()}
        onShowThinkingToggle={vi.fn()}
        onClearConversation={vi.fn()}
      />,
    );
    open();
    expect(items().map((i) => i.textContent)).toEqual([
      'Adjuntar archivo',
      'Cambiar idioma',
      'Formato de texto',
      'Copiar plantilla curl',
      'Ocultar razonamiento',
      'Limpiar conversación',
    ]);
  });

  it('keeps the per-item dress (danger, dev-tool) and the dividers', () => {
    render(<ChatToolbar onCopyCurl={vi.fn()} onClearConversation={vi.fn()} />);
    open();
    const curl = items().find((i) => i.textContent === 'Copiar plantilla curl')!;
    const clear = items().find((i) => i.textContent === 'Limpiar conversación')!;
    expect(curl.className).toContain('fi-text-warning');
    expect(clear.className).toContain('chat-dropdown-item-danger');
    expect(document.querySelectorAll('.chat-dropdown-divider').length).toBeGreaterThan(0);
  });

  it('keeps the compact-only gate on the entries that have their own button when there is room', () => {
    render(<ChatToolbar onShowThinkingToggle={vi.fn()} onClearConversation={vi.fn()} />);
    open();
    const clear = items().find((i) => i.textContent === 'Limpiar conversación')!;
    expect(clear.closest('.\\@md\\:hidden')).not.toBeNull();
  });

  it('still portals out of the composer and opens upward', () => {
    render(<ChatToolbar onAttach={vi.fn()} />);
    open();
    const menu = document.querySelector('[data-fi-action-menu]') as HTMLElement;
    expect(document.body.contains(menu)).toBe(true);
    expect(menu.style.transform).toBe('translateY(-100%)');
    expect(menu.className).toBe('chat-dropdown');
  });

  it('choosing "Adjuntar archivo" attaches and closes', () => {
    const onAttach = vi.fn();
    render(<ChatToolbar onAttach={onAttach} />);
    open();
    fireEvent.click(items()[0]);
    expect(onAttach).toHaveBeenCalledTimes(1);
    expect(document.querySelector('[data-fi-action-menu]')).toBeNull();
  });

  it('hides an entry whose handler the app did not wire', () => {
    render(<ChatToolbar onAttach={vi.fn()} showLanguage={false} showFormatting={false} showCopyCurl={false} showThinkingToggle={false} showClear={false} />);
    open();
    expect(items().map((i) => i.textContent)).toEqual(['Adjuntar archivo']);
  });
});
