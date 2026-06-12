// @vitest-environment jsdom

/**
 * Tests for AutoResizeTextarea sizing (B3-FIGLASS-15 + B3-FIGLASS-16).
 *
 * B3-FIGLASS-15: the empty composer must collapse to ONE line — the old
 * hardcoded 20px line height computed ceil(24/20) = 2 rows for an empty
 * textarea under the default 16px/24px font, permanently inflating it.
 *
 * B3-FIGLASS-16: the textarea must SHRINK when content is deleted. A real
 * textarea's scrollHeight never reports less than the height its `rows`
 * attribute imposes, so measuring without first resetting rows to 1 meant the
 * composer grew on type but never shrank on delete. jsdom reports scrollHeight
 * 0, which hides the bug — `mockDomScrollHeight` reproduces the real DOM
 * contract (max of content lines and the rows floor) so the shrink path is
 * actually exercised.
 */

import { describe, it, expect, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { AutoResizeTextarea } from './AutoResizeTextarea';

const SCROLL_HEIGHT = Object.getOwnPropertyDescriptor(
  HTMLElement.prototype,
  'scrollHeight',
);
const LINE_HEIGHT = 20; // jsdom line-height is 'normal' → component falls back to 20px

function mockScrollHeight(value: number) {
  Object.defineProperty(HTMLElement.prototype, 'scrollHeight', {
    configurable: true,
    get: () => value,
  });
}

/**
 * Faithful DOM behavior: scrollHeight = max(content lines, rows attribute) ×
 * line height. The `rows` floor is what made the pre-FIGLASS-16 measurement
 * sticky — a leftover rows=5 forced scrollHeight to 5 rows on empty content.
 */
function mockDomScrollHeight() {
  Object.defineProperty(HTMLElement.prototype, 'scrollHeight', {
    configurable: true,
    get(this: HTMLElement) {
      if (!(this instanceof HTMLTextAreaElement)) return 0;
      const lines = Math.max(1, this.value.split('\n').length);
      return Math.max(lines, this.rows) * LINE_HEIGHT;
    },
  });
}

afterEach(() => {
  cleanup();
  if (SCROLL_HEIGHT) {
    Object.defineProperty(HTMLElement.prototype, 'scrollHeight', SCROLL_HEIGHT);
  }
});

describe('AutoResizeTextarea sizing', () => {
  it('collapses an empty textarea to a single row (never 0, never inflated)', () => {
    mockScrollHeight(0); // jsdom default — exercises the 1-row floor
    const { container } = render(
      <AutoResizeTextarea value="" onChange={() => {}} />,
    );
    const ta = container.querySelector('textarea')!;
    expect(ta.rows).toBe(1);
    expect(ta.style.height).toBe('20px'); // 1 row × 20px fallback line height
  });

  it('grows with content up to maxRows and caps there', () => {
    mockDomScrollHeight();
    const { container } = render(
      <AutoResizeTextarea value={'línea\n'.repeat(10)} onChange={() => {}} maxRows={5} />,
    );
    const ta = container.querySelector('textarea')!;
    expect(ta.rows).toBe(5);
    expect(ta.style.height).toBe('100px'); // 5 × 20px fallback
  });

  it('grows from 1 to 5 rows as lines are typed', () => {
    mockDomScrollHeight();
    const { container, rerender } = render(
      <AutoResizeTextarea value="una línea" onChange={() => {}} maxRows={5} />,
    );
    const ta = container.querySelector('textarea')!;
    expect(ta.rows).toBe(1);

    rerender(
      <AutoResizeTextarea
        value={'uno\ndos\ntres\ncuatro\ncinco'}
        onChange={() => {}}
        maxRows={5}
      />,
    );
    expect(ta.rows).toBe(5);
    expect(ta.style.height).toBe('100px');
  });

  it('shrinks from 5 rows back to 1 when lines are deleted (B3-FIGLASS-16)', () => {
    mockDomScrollHeight();
    const { container, rerender } = render(
      <AutoResizeTextarea
        value={'uno\ndos\ntres\ncuatro\ncinco'}
        onChange={() => {}}
        maxRows={5}
      />,
    );
    const ta = container.querySelector('textarea')!;
    expect(ta.rows).toBe(5);

    rerender(
      <AutoResizeTextarea value="una línea" onChange={() => {}} maxRows={5} />,
    );
    expect(ta.rows).toBe(1);
    expect(ta.style.height).toBe('20px');
  });

  it('shrinks back to 1 row when ALL content is deleted (B3-FIGLASS-16)', () => {
    mockDomScrollHeight();
    const { container, rerender } = render(
      <AutoResizeTextarea
        value={'uno\ndos\ntres\ncuatro\ncinco'}
        onChange={() => {}}
        maxRows={5}
      />,
    );
    const ta = container.querySelector('textarea')!;
    expect(ta.rows).toBe(5);

    rerender(<AutoResizeTextarea value="" onChange={() => {}} maxRows={5} />);
    expect(ta.rows).toBe(1);
    expect(ta.style.height).toBe('20px');
  });

  it('still respects maxRows after a shrink/grow cycle', () => {
    mockDomScrollHeight();
    const { container, rerender } = render(
      <AutoResizeTextarea value={'x\n'.repeat(9)} onChange={() => {}} maxRows={5} />,
    );
    const ta = container.querySelector('textarea')!;
    expect(ta.rows).toBe(5);

    rerender(<AutoResizeTextarea value="" onChange={() => {}} maxRows={5} />);
    expect(ta.rows).toBe(1);

    rerender(
      <AutoResizeTextarea value={'x\n'.repeat(9)} onChange={() => {}} maxRows={5} />,
    );
    expect(ta.rows).toBe(5);
    expect(ta.style.height).toBe('100px');
  });

  it('collapses to 1 row after a send-style reset (multiline → empty)', () => {
    mockDomScrollHeight();
    // Send clears the controlled value in one shot, exactly like deleting all
    // content — the composer must not keep a ghost multi-row box.
    const { container, rerender } = render(
      <AutoResizeTextarea
        value={'mensaje\nlargo\nde\nvarias\nlíneas'}
        onChange={() => {}}
        maxRows={5}
      />,
    );
    const ta = container.querySelector('textarea')!;
    expect(ta.rows).toBe(5);

    rerender(<AutoResizeTextarea value="" onChange={() => {}} maxRows={5} />);
    expect(ta.rows).toBe(1);
    expect(ta.style.height).toBe('20px');
  });
});
