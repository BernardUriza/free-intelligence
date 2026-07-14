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

  it('renders footerStart inside the footer slot, led by the rail disclosure toggle', () => {
    render(
      <ComposerFrame
        footerStart={<button>persona</button>}
        footerStartClassName="rail"
        footer={<button>send</button>}
      >
        <textarea aria-label="body" />
      </ComposerFrame>
    );
    const start = slot('footer-start');
    expect(start).not.toBeNull();
    expect(start!.className).toBe('rail');
    expect(start!.parentElement).toBe(slot('footer'));
    // CONV-MOBILE-RECLAIM-1: the compact-mode disclosure toggle leads the
    // footer (display:none on wide containers) and announces its state; the
    // rail follows it and starts collapsed.
    const toggle = slot('footer')!.firstElementChild!;
    expect(toggle.getAttribute('aria-label')).toBe('Más opciones');
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    expect(toggle.getAttribute('aria-controls')).toBe(start!.id);
    expect(toggle.nextElementSibling).toBe(start);
  });

  it('mounts the footer for a footerStart even when there is no footer content', () => {
    render(
      <ComposerFrame footerStart={<button>persona</button>}>
        <textarea aria-label="body" />
      </ComposerFrame>
    );
    expect(slot('footer')).not.toBeNull();
    expect(slot('footer-start')!.textContent).toBe('persona');
  });

  // The whole point of `margin-right: auto` over flipping `justify-content`:
  // every existing consumer's footer must be untouched.
  it('leaves a footer without footerStart byte-identical — no rail wrapper', () => {
    render(
      <ComposerFrame footer={<button>send</button>} footerClassName="ctl">
        <textarea aria-label="body" />
      </ComposerFrame>
    );
    expect(slot('footer-start')).toBeNull();
    expect(slot('footer')!.children.length).toBe(1);
    expect(slot('footer')!.firstElementChild!.tagName).toBe('BUTTON');
  });

  it('treats a `false` footerStart as empty — no ghost rail', () => {
    render(
      <ComposerFrame footerStart={false} footer={<button>send</button>}>
        <textarea aria-label="body" />
      </ComposerFrame>
    );
    expect(slot('footer-start')).toBeNull();
  });

  it('keeps the left rail reachable: footerStart claims it with margin-right auto', () => {
    render(
      <ComposerFrame footerStart={<span>chip</span>}>
        <textarea aria-label="body" />
      </ComposerFrame>
    );
    const css = document.getElementById('fi-composer-frame-style')!.textContent!;
    expect(css).toContain('[data-fi-composer-slot="footer-start"]');
    expect(css).toContain('margin-right: auto');
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
