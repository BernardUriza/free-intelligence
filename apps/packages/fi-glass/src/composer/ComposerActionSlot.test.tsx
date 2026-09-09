// @vitest-environment jsdom
/**
 * The composer control's anatomy lives in the framework; its colour does not.
 *
 * The regression these pin: og118 had written the same five layout declarations
 * three times in `globals.css` and re-derived the 44×44 minimum for a narrow
 * composer by hand — and the next shell would have written them a fourth time.
 * The inverse regression matters as much: the day this primitive ships a
 * colour, every shell starts looking like og118.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, cleanup, fireEvent } from '@testing-library/react';
import { ComposerActionSlot } from './ComposerActionSlot';
import {
  FI_COMPOSER_ACTION_CLASS,
  FI_COMPOSER_ACTION_LABEL_CLASS,
  FI_COMPOSER_ACTION_VARIANT_CLASS,
} from './composerActionStyle';

const button = () => document.querySelector('button') as HTMLButtonElement;
const sheet = () =>
  (document.getElementById('fi-composer-action-style')?.textContent ?? '');

describe('<ComposerActionSlot>', () => {
  afterEach(() => {
    cleanup();
    document.getElementById('fi-composer-action-style')?.remove();
  });

  it('defaults to the secondary chip and carries the base + variant classes', () => {
    render(<ComposerActionSlot icon={<svg />} label="Llamar" />);
    expect(button().className).toContain(FI_COMPOSER_ACTION_CLASS);
    expect(button().className).toContain(FI_COMPOSER_ACTION_VARIANT_CLASS.secondary);
    expect(button().type).toBe('button');
  });

  it('renders the primary variant when asked, and keeps the consumer class', () => {
    render(
      <ComposerActionSlot variant="primary" icon={<svg />} className="og-send-btn" />,
    );
    expect(button().className).toContain(FI_COMPOSER_ACTION_VARIANT_CLASS.primary);
    expect(button().className).toContain('og-send-btn');
  });

  it('composes the touch-target class rather than replacing it', () => {
    render(<ComposerActionSlot icon={<svg />} className="og-resonance-call-btn" />);
    expect(button().className).toContain('fi-touch-target');
    expect(button().className).toContain('og-resonance-call-btn');
  });

  it('hides the label on a compact composer by default, and honours the opt-out', () => {
    const { rerender } = render(<ComposerActionSlot icon={<svg />} label="Llamar" />);
    const label = document.querySelector(`.${FI_COMPOSER_ACTION_LABEL_CLASS}`)!;
    expect(label.hasAttribute('data-fi-compact-hide')).toBe(true);
    expect(sheet()).toContain('@container fi-composer (max-width: 420px)');
    expect(sheet()).toContain(`.${FI_COMPOSER_ACTION_LABEL_CLASS}[data-fi-compact-hide]`);

    rerender(<ComposerActionSlot icon={<svg />} label="Llamar" hideLabelWhenCompact={false} />);
    expect(
      document.querySelector(`.${FI_COMPOSER_ACTION_LABEL_CLASS}`)!.hasAttribute('data-fi-compact-hide'),
    ).toBe(false);
  });

  it('renders no label element when there is nothing to label', () => {
    render(<ComposerActionSlot icon={<svg />} aria-label="Llamar por voz" />);
    expect(document.querySelector(`.${FI_COMPOSER_ACTION_LABEL_CLASS}`)).toBeNull();
    expect(button().getAttribute('aria-label')).toBe('Llamar por voz');
  });

  it('emits the rail-keep contract only when the control must survive the collapse', () => {
    const { rerender } = render(<ComposerActionSlot icon={<svg />} />);
    expect(button().hasAttribute('data-fi-rail-keep')).toBe(false);
    rerender(<ComposerActionSlot icon={<svg />} keepWhenRailCollapses />);
    expect(button().hasAttribute('data-fi-rail-keep')).toBe(true);
  });

  it('keeps its box when disabled — unavailable, not absent', () => {
    render(<ComposerActionSlot variant="primary" icon={<svg />} disabled />);
    expect(button().disabled).toBe(true);
    expect(button().className).toContain(FI_COMPOSER_ACTION_VARIANT_CLASS.primary);
    const disabledRule = sheet().split(`.${FI_COMPOSER_ACTION_CLASS}:disabled)`)[1].split('}')[0];
    expect(disabledRule).toContain('cursor: not-allowed');
    expect(disabledRule).not.toContain('display');
    expect(disabledRule).not.toContain('padding');
  });

  it('forwards the click and every native button attribute', () => {
    const onClick = vi.fn();
    render(
      <ComposerActionSlot icon={<svg />} onClick={onClick} aria-pressed data-ref="probe" />,
    );
    fireEvent.click(button());
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(button().getAttribute('aria-pressed')).toBe('true');
    expect(button().getAttribute('data-ref')).toBe('probe');
  });

  it('states its defaults at zero specificity so a consumer class always wins', () => {
    // The sheet is injected at runtime and lands after the app stylesheet, so an
    // un-wrapped default would beat the consumer at every tie — it erased og118's
    // send gradient the first time this was measured in Chrome.
    render(<ComposerActionSlot icon={<svg />} />);
    const css = sheet();
    for (const decl of ['background: transparent', 'color: inherit', 'border: 1px solid transparent']) {
      const rule = css.split(decl)[0].split('\n').reverse().find((l) => l.includes('{'))!;
      expect(rule).toContain(':where(');
    }
  });

  it('owns the shape and the touch minimum, and no colour at all', () => {
    render(<ComposerActionSlot icon={<svg />} />);
    const css = sheet();
    expect(css).toContain('min-width: var(--fi-touch-target, 44px)');
    // The minimum is on the BASE class, so send gets it too — shell/touchTarget
    // is viewport-gated and misses a narrow composer on a wide screen.
    const compact = css.split('@container fi-composer (max-width: 420px)')[1];
    expect(compact).toContain(`.${FI_COMPOSER_ACTION_CLASS} {`);
    // A guarantee, not a default: the minimum keeps real specificity so no
    // consumer class can shrink a target back to win space.
    expect(compact).not.toContain(`:where(.${FI_COMPOSER_ACTION_CLASS}) {`);
    expect(css).toContain('border-radius: var(--fi-composer-action-pill-radius, 999px)');
    expect(css).toContain('background: transparent');
    expect(css).toContain('color: inherit');
    // No brand: the sheet must not name a colour of its own.
    expect(css).not.toMatch(/#[0-9a-f]{3,8}\b/i);
    expect(css).not.toMatch(/\brgba?\(/i);
  });

  it('injects its stylesheet once no matter how many controls mount', () => {
    render(
      <>
        <ComposerActionSlot icon={<svg />} />
        <ComposerActionSlot icon={<svg />} variant="primary" />
      </>,
    );
    expect(document.querySelectorAll('#fi-composer-action-style')).toHaveLength(1);
  });
});
