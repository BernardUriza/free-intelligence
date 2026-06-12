// @vitest-environment jsdom

/**
 * Tests for AutoResizeTextarea sizing (B3-FIGLASS-15).
 *
 * The empty composer must collapse to ONE line: the old hardcoded 20px line
 * height computed ceil(24/20) = 2 rows for an empty textarea under the default
 * 16px/24px font, permanently inflating the composer. jsdom reports
 * scrollHeight 0 and line-height 'normal', which exercises both guards: the
 * 1-row floor and the 20px fallback.
 */

import { describe, it, expect, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { AutoResizeTextarea } from './AutoResizeTextarea';

const SCROLL_HEIGHT = Object.getOwnPropertyDescriptor(
  HTMLElement.prototype,
  'scrollHeight',
);

function mockScrollHeight(value: number) {
  Object.defineProperty(HTMLElement.prototype, 'scrollHeight', {
    configurable: true,
    get: () => value,
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
    mockScrollHeight(200); // ceil(200/20) = 10 → capped at maxRows
    const { container } = render(
      <AutoResizeTextarea value={'línea\n'.repeat(10)} onChange={() => {}} maxRows={5} />,
    );
    const ta = container.querySelector('textarea')!;
    expect(ta.rows).toBe(5);
    expect(ta.style.height).toBe('100px'); // 5 × 20px fallback
  });
});
