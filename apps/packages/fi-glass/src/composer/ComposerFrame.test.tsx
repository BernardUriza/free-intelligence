// @vitest-environment jsdom
/**
 * Tests for ComposerFrame — the header/body/footer slot anatomy
 * (B3-FIGLASS-COMPOSER-FRAME-1).
 *
 * The contract under test: one container; the body renders directly (no
 * wrapper element, so existing consumers' box layout is unchanged); the
 * header/footer slot wrappers exist ONLY when the slot is filled; slot order
 * is header → body → footer; the tokenized stylesheet injects once.
 */

import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { ComposerFrame } from './ComposerFrame';

const frame = () => document.querySelector('[data-fi-composer-frame]');
const slot = (name: string) =>
  document.querySelector(`[data-fi-composer-slot="${name}"]`);

describe('<ComposerFrame> slots', () => {
  afterEach(cleanup);

  it('renders only the container and the body when no header/footer', () => {
    render(
      <ComposerFrame className="box">
        <textarea aria-label="body" />
      </ComposerFrame>
    );
    expect(frame()).not.toBeNull();
    expect(frame()!.className).toBe('box');
    expect(screen.getByLabelText('body')).toBeTruthy();
    expect(slot('header')).toBeNull();
    expect(slot('footer')).toBeNull();
    // The body is a DIRECT child — no extra wrapper between container and body.
    expect(screen.getByLabelText('body').parentElement).toBe(frame());
  });

  it('renders the header slot before the body when provided', () => {
    render(
      <ComposerFrame header={<span>draft</span>} headerClassName="hdr">
        <textarea aria-label="body" />
      </ComposerFrame>
    );
    const header = slot('header');
    expect(header).not.toBeNull();
    expect(header!.className).toBe('hdr');
    expect(header!.textContent).toBe('draft');
    const children = [...frame()!.children];
    expect(children.indexOf(header as Element)).toBeLessThan(
      children.indexOf(screen.getByLabelText('body'))
    );
  });

  it('renders the footer slot after the body when provided', () => {
    render(
      <ComposerFrame footer={<button>send</button>} footerClassName="ctl">
        <textarea aria-label="body" />
      </ComposerFrame>
    );
    const footer = slot('footer');
    expect(footer).not.toBeNull();
    expect(footer!.className).toBe('ctl');
    expect(footer!.textContent).toBe('send');
    const children = [...frame()!.children];
    expect(children.indexOf(footer as Element)).toBeGreaterThan(
      children.indexOf(screen.getByLabelText('body'))
    );
  });

  it('always renders the body, with all three slots in order', () => {
    render(
      <ComposerFrame header={<span>h</span>} footer={<span>f</span>}>
        <textarea aria-label="body" />
      </ComposerFrame>
    );
    const order = [...frame()!.children].map(
      (el) => el.getAttribute('data-fi-composer-slot') ?? 'body'
    );
    expect(order).toEqual(['header', 'body', 'footer']);
  });

  it('treats a `false` slot (the `cond && <X/>` pattern) as empty — no ghost row', () => {
    render(
      <ComposerFrame header={false} footer={false}>
        <textarea aria-label="body" />
      </ComposerFrame>
    );
    expect(slot('header')).toBeNull();
    expect(slot('footer')).toBeNull();
  });

  it('injects the tokenized stylesheet once', () => {
    render(
      <ComposerFrame footer={<span>f</span>}>
        <textarea aria-label="body" />
      </ComposerFrame>
    );
    const sheets = document.querySelectorAll('#fi-composer-frame-style');
    expect(sheets.length).toBe(1);
    expect(sheets[0].textContent).toContain('--fi-space-2');
  });
});
