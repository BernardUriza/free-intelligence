// @vitest-environment jsdom
/**
 * MessageBubble — touch actions-reveal contracts (CONV-MOBILE-RECLAIM-1).
 *
 * Pins the two behaviors the mobile reclaim promised: tapping a bubble toggles
 * its actions row, and opening one bubble CLOSES every other open one (a single
 * contextual toolbar at a time — otherwise the rows accumulate and re-spend the
 * viewport the refactor reclaimed). Also pins that taps on interactive
 * descendants never double as a toggle.
 */
import { describe, it, expect, afterEach } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MessageBubble } from './MessageBubble';

afterEach(cleanup);

function bubbles() {
  return render(
    <>
      <MessageBubble role="user" ariaLabel="m1" actions={<span>a1</span>}>
        <p>uno</p>
      </MessageBubble>
      <MessageBubble role="assistant" ariaLabel="m2" actions={<span>a2</span>}>
        <p>dos</p>
        <button type="button">inner</button>
      </MessageBubble>
    </>,
  );
}

const article = (label: string) => screen.getByRole('article', { name: label });

describe('MessageBubble — actions reveal', () => {
  it('tap toggles data-fi-actions-open on the bubble', () => {
    bubbles();
    const m1 = article('m1');
    expect(m1.hasAttribute('data-fi-actions-open')).toBe(false);
    fireEvent.click(m1);
    expect(m1.hasAttribute('data-fi-actions-open')).toBe(true);
    fireEvent.click(m1);
    expect(m1.hasAttribute('data-fi-actions-open')).toBe(false);
  });

  it('opening one bubble closes the previously open one', () => {
    bubbles();
    const m1 = article('m1');
    const m2 = article('m2');
    fireEvent.click(m1);
    expect(m1.hasAttribute('data-fi-actions-open')).toBe(true);
    fireEvent.click(m2);
    expect(m2.hasAttribute('data-fi-actions-open')).toBe(true);
    expect(m1.hasAttribute('data-fi-actions-open')).toBe(false);
  });

  it('a tap on an interactive descendant never toggles the reveal', () => {
    bubbles();
    const m2 = article('m2');
    fireEvent.click(screen.getByRole('button', { name: 'inner' }));
    expect(m2.hasAttribute('data-fi-actions-open')).toBe(false);
  });

  it('a bubble without actions renders no actions container and ignores taps', () => {
    render(
      <MessageBubble role="user" ariaLabel="solo">
        <p>sin acciones</p>
      </MessageBubble>,
    );
    const m = article('solo');
    fireEvent.click(m);
    expect(m.hasAttribute('data-fi-actions-open')).toBe(false);
    expect(m.querySelector('.fi-msg-actions')).toBeNull();
  });
});
