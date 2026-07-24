'use client';

/**
 * fi-glass · useEdgeSwipe — the native drawer gesture (B3-FIGLASS-SWIPE-1).
 *
 * The off-canvas drawer of AgentWorkspaceShell opened only by tapping the
 * hamburger. On a phone the expected affordance is the gesture: drag from the
 * left edge to the right to pull the panel in, drag left to push it back out,
 * with the panel FOLLOWING the finger and settling by distance or flick speed.
 *
 * It is deliberately a shell-level primitive (not agent-level): any drawer
 * surface can consume it. The hook owns only the gesture math and returns a
 * 0..1 `progress` while a drag is live (`null` otherwise) — the consumer decides
 * how that paints, so fi-glass never assumes a visual.
 *
 * Contract notes:
 *  - touch only. A mouse/trackpad has no edge-swipe idiom and a pointer version
 *    would fight text selection.
 *  - the axis is decided once per gesture: past the slop, a mostly-vertical move
 *    releases the gesture so the conversation/list keeps scrolling normally.
 *  - listeners are native + `{ passive: false }`; React's delegated touch
 *    handlers cannot preventDefault the horizontal pan.
 */

import { useEffect, useRef, useState, type RefObject } from 'react';

export interface EdgeSwipeOptions {
  /** Master switch — the consumer passes `false` outside drawer mode. */
  enabled: boolean;
  /** Current drawer state: decides whether a gesture opens or closes. */
  isOpen: boolean;
  /** Element the gesture is listened on (the shell root). */
  containerRef: RefObject<HTMLElement | null>;
  /** The drawer panel — measured to convert pixels into progress. */
  panelRef: RefObject<HTMLElement | null>;
  onOpen: () => void;
  onClose: () => void;
  /** Width of the left hot zone that starts an OPEN gesture. Default 24px. */
  edgeSize?: number;
  /** Used when the panel cannot be measured (SSR/jsdom). Default 280px. */
  fallbackWidth?: number;
  /** Fraction of the panel width that commits the gesture. Default 0.4. */
  distanceRatio?: number;
  /** Flick speed (px/ms) that commits regardless of distance. Default 0.35. */
  velocity?: number;
  /** Movement before the axis is decided. Default 8px. */
  axisSlop?: number;
}

interface GestureState {
  id: number;
  startX: number;
  startY: number;
  startTime: number;
  width: number;
  opening: boolean;
  axis: 'undecided' | 'horizontal';
}

const clamp01 = (n: number): number => (n < 0 ? 0 : n > 1 ? 1 : n);

export function useEdgeSwipe({
  enabled,
  isOpen,
  containerRef,
  panelRef,
  onOpen,
  onClose,
  edgeSize = 24,
  fallbackWidth = 280,
  distanceRatio = 0.4,
  velocity = 0.35,
  axisSlop = 8,
}: EdgeSwipeOptions): number | null {
  const [progress, setProgress] = useState<number | null>(null);
  const gestureRef = useRef<GestureState | null>(null);

  useEffect(() => {
    if (!enabled) {
      gestureRef.current = null;
      setProgress(null);
      return;
    }
    const node = containerRef.current;
    if (!node) return;

    const measure = (): number => {
      const measured = panelRef.current?.getBoundingClientRect().width ?? 0;
      return measured > 0 ? measured : fallbackWidth;
    };

    const release = (): void => {
      gestureRef.current = null;
      setProgress(null);
    };

    const handleStart = (event: TouchEvent): void => {
      if (gestureRef.current || event.touches.length !== 1) return;
      const touch = event.touches[0];
      if (!isOpen && touch.clientX > edgeSize) return;
      gestureRef.current = {
        id: touch.identifier,
        startX: touch.clientX,
        startY: touch.clientY,
        startTime: Date.now(),
        width: measure(),
        opening: !isOpen,
        axis: 'undecided',
      };
    };

    const handleMove = (event: TouchEvent): void => {
      const gesture = gestureRef.current;
      if (!gesture) return;
      const touch = Array.from(event.touches).find((t) => t.identifier === gesture.id);
      if (!touch) return;

      const dx = touch.clientX - gesture.startX;
      const dy = touch.clientY - gesture.startY;

      if (gesture.axis === 'undecided') {
        if (Math.abs(dx) < axisSlop && Math.abs(dy) < axisSlop) return;
        if (Math.abs(dx) <= Math.abs(dy)) {
          release();
          return;
        }
        gesture.axis = 'horizontal';
      }

      if (event.cancelable) event.preventDefault();
      setProgress(clamp01(gesture.opening ? dx / gesture.width : 1 + dx / gesture.width));
    };

    const handleEnd = (event: TouchEvent): void => {
      const gesture = gestureRef.current;
      if (!gesture) return;
      const touch = Array.from(event.changedTouches).find((t) => t.identifier === gesture.id);
      release();
      if (!touch || gesture.axis !== 'horizontal') return;

      const dx = touch.clientX - gesture.startX;
      const elapsed = Math.max(1, Date.now() - gesture.startTime);
      const speed = dx / elapsed;
      const travelled = gesture.opening ? dx : -dx;
      const flicked = gesture.opening ? speed > velocity : -speed > velocity;

      if (travelled > gesture.width * distanceRatio || flicked) {
        if (gesture.opening) onOpen();
        else onClose();
      }
    };

    node.addEventListener('touchstart', handleStart, { passive: true });
    node.addEventListener('touchmove', handleMove, { passive: false });
    node.addEventListener('touchend', handleEnd, { passive: true });
    node.addEventListener('touchcancel', release, { passive: true });

    return () => {
      node.removeEventListener('touchstart', handleStart);
      node.removeEventListener('touchmove', handleMove);
      node.removeEventListener('touchend', handleEnd);
      node.removeEventListener('touchcancel', release);
      gestureRef.current = null;
    };
  }, [
    enabled,
    isOpen,
    containerRef,
    panelRef,
    onOpen,
    onClose,
    edgeSize,
    fallbackWidth,
    distanceRatio,
    velocity,
    axisSlop,
  ]);

  return progress;
}
