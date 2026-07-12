// @vitest-environment jsdom
/**
 * The shared "+" — one trigger for every add-to-this-turn capability.
 *
 * The regression it prevents: a composer that grows one icon button per feature
 * (og118's ImagePlus) or buries the most common action two clicks deep inside an
 * overflow menu next to a dev tool (aurity's "⋮ Más opciones" → "Adjuntar
 * archivo"). One trigger, N actions, in the framework — not in each app.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, cleanup, fireEvent } from '@testing-library/react';
import { ComposerActions, type ComposerAction } from './ComposerActions';

const trigger = () => document.querySelector('[data-fi-composer-actions]') as HTMLButtonElement;
const menu = () => document.querySelector('[data-fi-action-menu]');
const items = () => Array.from(document.querySelectorAll('[role="menuitem"]'));

const action = (over: Partial<ComposerAction> = {}): ComposerAction => ({
  id: 'attach-image',
  label: 'Adjuntar imagen',
  onSelect: vi.fn(),
  ...over,
});

describe('<ComposerActions>', () => {
  afterEach(cleanup);

  it('renders nothing when there is no capability to offer', () => {
    render(<ComposerActions actions={[]} />);
    expect(trigger()).toBeNull();
  });

  it('the menu is closed until the "+" is pressed', () => {
    render(<ComposerActions actions={[action()]} />);
    expect(trigger()).not.toBeNull();
    expect(trigger().getAttribute('aria-expanded')).toBe('false');
    expect(menu()).toBeNull();

    fireEvent.click(trigger());
    expect(trigger().getAttribute('aria-expanded')).toBe('true');
    expect(items().map((i) => i.textContent)).toEqual(['Adjuntar imagen']);
  });

  it('every capability lands in the SAME menu (this is the point)', () => {
    render(
      <ComposerActions
        actions={[
          action(),
          action({ id: 'upload-doc', label: 'Subir documento al proyecto' }),
        ]}
      />,
    );
    fireEvent.click(trigger());
    expect(items().map((i) => i.textContent)).toEqual([
      'Adjuntar imagen',
      'Subir documento al proyecto',
    ]);
  });

  it('choosing an action runs it and closes the menu', () => {
    const onSelect = vi.fn();
    render(<ComposerActions actions={[action({ onSelect })]} />);
    fireEvent.click(trigger());
    fireEvent.click(items()[0]);
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(menu()).toBeNull();
  });

  it('a disabled action does not run', () => {
    const onSelect = vi.fn();
    render(<ComposerActions actions={[action({ onSelect, disabled: true })]} />);
    fireEvent.click(trigger());
    fireEvent.click(items()[0]);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('Escape dismisses the menu', () => {
    render(<ComposerActions actions={[action()]} />);
    fireEvent.click(trigger());
    expect(menu()).not.toBeNull();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(menu()).toBeNull();
  });

  it("an outside click dismisses the menu (aurity's backdrop)", () => {
    render(<ComposerActions actions={[action()]} />);
    fireEvent.click(trigger());
    const backdrop = document.querySelector('[aria-hidden="true"]') as HTMLElement;
    expect(backdrop).not.toBeNull();
    fireEvent.click(backdrop);
    expect(menu()).toBeNull();
  });

  it("renders aurity's anatomy: portaled to body, opening upward", () => {
    render(<ComposerActions actions={[action()]} />);
    fireEvent.click(trigger());
    const m = menu() as HTMLElement;
    // Portaled OUT of the composer (which clips with overflow:hidden).
    expect(m.closest('[data-fi-composer-actions]')).toBeNull();
    expect(document.body.contains(m)).toBe(true);
    expect(m.style.transform).toBe('translateY(-100%)');
  });

  it('the trigger is disabled while a turn streams', () => {
    render(<ComposerActions actions={[action()]} disabled />);
    expect(trigger().disabled).toBe(true);
  });
});
