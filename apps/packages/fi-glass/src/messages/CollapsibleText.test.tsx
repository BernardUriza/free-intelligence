// @vitest-environment jsdom

/**
 * Tests for CollapsibleText (B3-FIGLASS-12) — the ChatGPT-parity disclosure
 * clamp. jsdom reports scrollHeight 0 for everything, so overflow is simulated
 * by redefining the scrollHeight getter on HTMLElement.prototype per test.
 *
 * Contract pinned here:
 *  - content that FITS renders whole, with no toggle;
 *  - content that OVERFLOWS clamps (maxHeight + mask) behind an accessible
 *    disclosure (aria-expanded + aria-controls);
 *  - toggling expands (clamp removed, label flips) and collapses back;
 *  - copy + toggle class are consumer-overridable.
 */

import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { CollapsibleText } from './CollapsibleText';

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
  vi.restoreAllMocks();
  if (SCROLL_HEIGHT) {
    Object.defineProperty(HTMLElement.prototype, 'scrollHeight', SCROLL_HEIGHT);
  }
});

describe('CollapsibleText', () => {
  it('renders children whole with no toggle when content fits', () => {
    mockScrollHeight(100); // under default 264 + 16 tolerance
    render(<CollapsibleText>corto</CollapsibleText>);
    expect(screen.getByText('corto')).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('clamps overflowing content behind an accessible disclosure', () => {
    mockScrollHeight(600); // over default 264 + 16
    render(<CollapsibleText>larguísimo</CollapsibleText>);

    const toggle = screen.getByRole('button', { name: 'Mostrar más' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');

    const content = document.getElementById(
      toggle.getAttribute('aria-controls')!,
    )!;
    expect(content).toHaveTextContent('larguísimo');
    expect(content.style.maxHeight).toBe('264px');
    expect(content.style.overflow).toBe('hidden');
    expect(content.style.maskImage).toContain('linear-gradient');
  });

  it('expands on toggle (clamp removed, label flips) and collapses back', () => {
    mockScrollHeight(600);
    render(<CollapsibleText>larguísimo</CollapsibleText>);

    const toggle = screen.getByRole('button', { name: 'Mostrar más' });
    fireEvent.click(toggle);

    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(toggle).toHaveTextContent('Mostrar menos');
    const content = document.getElementById(
      toggle.getAttribute('aria-controls')!,
    )!;
    expect(content.style.maxHeight).toBe('');

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(content.style.maxHeight).toBe('264px');
  });

  it('honors custom maxHeight, labels and toggle class', () => {
    mockScrollHeight(600);
    render(
      <CollapsibleText
        maxHeight={120}
        showMoreLabel="Ver todo"
        showLessLabel="Ver menos"
        toggleClassName="og-toggle"
      >
        larguísimo
      </CollapsibleText>,
    );

    const toggle = screen.getByRole('button', { name: 'Ver todo' });
    expect(toggle).toHaveClass('og-toggle');
    // Consumer class drops the default inline skin.
    expect(toggle.style.textDecoration).toBe('');
    const content = document.getElementById(
      toggle.getAttribute('aria-controls')!,
    )!;
    expect(content.style.maxHeight).toBe('120px');

    fireEvent.click(toggle);
    expect(screen.getByRole('button', { name: 'Ver menos' })).toBeInTheDocument();
  });
});
