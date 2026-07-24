// @vitest-environment jsdom

/**
 * Edge-swipe gesture for the AgentWorkspaceShell drawer (B3-FIGLASS-SWIPE-1).
 *
 * The sibling `.drawer` file pins the tap/Escape/render-prop paths; this one
 * pins the gesture contract:
 *  - a drag right from the left edge follows the finger and commits past the
 *    distance threshold (and snaps back below it);
 *  - a drag starting away from the edge is ignored while closed;
 *  - a mostly-vertical move releases the gesture so lists keep scrolling;
 *  - while open, a drag left closes;
 *  - `swipe={false}` and desktop (non-drawer) mode listen to nothing.
 */

import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest';
import { render, cleanup, fireEvent } from '@testing-library/react';
import { clearMediaQueryCache } from '../shell/useMediaQuery';
import { AgentWorkspaceShell } from './AgentWorkspaceShell';

const PANEL_WIDTH = 280;

beforeEach(() => {
  clearMediaQueryCache();
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({
    width: PANEL_WIDTH,
    height: 800,
    top: 0,
    left: 0,
    right: PANEL_WIDTH,
    bottom: 800,
    x: 0,
    y: 0,
    toJSON: () => ({}),
  } as DOMRect);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function mockMatchMedia(matches: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

const touch = (x: number, y: number) => ({ identifier: 1, clientX: x, clientY: y });

const root = (container: HTMLElement): HTMLElement =>
  container.querySelector('[data-fi-workspace="agent-with-sidebar"]') as HTMLElement;

const panel = (container: HTMLElement): HTMLElement =>
  container.querySelector('[data-fi-slot="sidebar"]') as HTMLElement;

function renderShell(props: Record<string, unknown> = {}) {
  return render(
    <AgentWorkspaceShell
      responsive
      sidebar={<nav>list</nav>}
      conversation={<main>chat</main>}
      {...props}
    />,
  );
}

/** Drives a full gesture; `elapsedMs` fakes the clock so velocity is testable. */
function drag(
  container: HTMLElement,
  path: Array<[number, number]>,
  { elapsedMs = 600 }: { elapsedMs?: number } = {},
) {
  const node = root(container);
  const [[x0, y0]] = path;
  const t0 = Date.now();
  const nowSpy = vi.spyOn(Date, 'now').mockReturnValue(t0);
  fireEvent.touchStart(node, { touches: [touch(x0, y0)] });
  for (const [x, y] of path.slice(1)) {
    fireEvent.touchMove(node, { touches: [touch(x, y)] });
  }
  const [xEnd, yEnd] = path[path.length - 1];
  nowSpy.mockReturnValue(t0 + elapsedMs);
  fireEvent.touchEnd(node, { changedTouches: [touch(xEnd, yEnd)] });
  nowSpy.mockRestore();
}

describe('AgentWorkspaceShell — edge swipe (mobile drawer)', () => {
  beforeEach(() => mockMatchMedia(true));

  it('follows the finger from the left edge and commits past the threshold', () => {
    const { container } = renderShell();
    expect(panel(container).style.transform).toBe('translateX(-100%)');

    const node = root(container);
    const t0 = Date.now();
    const nowSpy = vi.spyOn(Date, 'now').mockReturnValue(t0);
    fireEvent.touchStart(node, { touches: [touch(4, 400)] });
    fireEvent.touchMove(node, { touches: [touch(74, 402)] });

    // 70px of a 280px panel = 25% in — the panel tracks the finger, un-animated.
    expect(panel(container).style.transform).toBe('translateX(-75%)');
    expect(panel(container).style.transition).toBe('none');
    expect(node.hasAttribute('data-fi-drawer-dragging')).toBe(true);

    fireEvent.touchMove(node, { touches: [touch(160, 402)] });
    nowSpy.mockReturnValue(t0 + 600);
    fireEvent.touchEnd(node, { changedTouches: [touch(160, 402)] });
    nowSpy.mockRestore();

    expect(panel(container).style.transform).toBe('translateX(0)');
    expect(panel(container).style.transition).toBe('transform 0.24s ease');
    expect(root(container).hasAttribute('data-fi-drawer-dragging')).toBe(false);
  });

  it('snaps back when the drag is short and slow', () => {
    const { container } = renderShell();
    drag(container, [[4, 400], [40, 402], [60, 402]], { elapsedMs: 800 });
    expect(panel(container).style.transform).toBe('translateX(-100%)');
  });

  it('commits a short but fast flick', () => {
    const { container } = renderShell();
    drag(container, [[4, 400], [40, 400], [60, 400]], { elapsedMs: 60 });
    expect(panel(container).style.transform).toBe('translateX(0)');
  });

  it('ignores a drag that does not start at the edge', () => {
    const { container } = renderShell();
    drag(container, [[200, 400], [340, 400]], { elapsedMs: 300 });
    expect(panel(container).style.transform).toBe('translateX(-100%)');
  });

  it('releases the gesture on a mostly-vertical move so lists keep scrolling', () => {
    const { container } = renderShell();
    const node = root(container);
    fireEvent.touchStart(node, { touches: [touch(6, 400)] });
    fireEvent.touchMove(node, { touches: [touch(12, 340)] });
    expect(node.hasAttribute('data-fi-drawer-dragging')).toBe(false);

    fireEvent.touchMove(node, { touches: [touch(200, 340)] });
    fireEvent.touchEnd(node, { changedTouches: [touch(200, 340)] });
    expect(panel(container).style.transform).toBe('translateX(-100%)');
  });

  it('closes with a leftward drag while open', () => {
    const { container } = renderShell();
    fireEvent.click(container.querySelector('.fi-aws-toggle') as HTMLElement);
    expect(panel(container).style.transform).toBe('translateX(0)');

    drag(container, [[240, 400], [160, 402], [80, 402]], { elapsedMs: 600 });
    expect(panel(container).style.transform).toBe('translateX(-100%)');
  });

  it('does nothing with swipe={false}', () => {
    const { container } = renderShell({ swipe: false });
    drag(container, [[4, 400], [200, 400]], { elapsedMs: 300 });
    expect(panel(container).style.transform).toBe('translateX(-100%)');
  });
});

describe('AgentWorkspaceShell — edge swipe (desktop)', () => {
  it('is inert outside drawer mode', () => {
    mockMatchMedia(false);
    const { container } = renderShell();
    const node = root(container);
    fireEvent.touchStart(node, { touches: [touch(4, 400)] });
    fireEvent.touchMove(node, { touches: [touch(200, 400)] });
    expect(node.hasAttribute('data-fi-drawer-dragging')).toBe(false);
    expect(panel(container).style.transform).toBe('');
  });
});
