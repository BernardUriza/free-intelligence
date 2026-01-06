'use client';

/**
 * OnboardingMessage - Rich message variant for onboarding flows
 *
 * Features:
 * - Rich markdown rendering with custom components
 * - Persona-based styling
 * - Timestamps and phase indicators
 * - Entrance animations
 * - Backend persona integration (usePersonas)
 *
 * This is currently an adapter wrapping FIMessageBubble.
 * Future: Refactor to use unified primitives from ../primitives/
 *
 * @see Headless Component Pattern: https://martinfowler.com/articles/headless-component.html
 */

import type { OnboardingMessageProps } from '../types';
import {
  FIMessageBubble,
  type FIMessageBubbleProps,
} from '@/components/onboarding/FIMessageBubble';

/**
 * OnboardingMessage - Adapter for FIMessageBubble
 *
 * Maps unified props to FIMessageBubble props.
 * Provides backwards compatibility while we migrate to unified primitives.
 */
export function OnboardingMessage({
  message,
  showTimestamp = true,
  showSenderName = true,
  animate = true,
  className,
  borderRadiusOverride,
}: OnboardingMessageProps) {
  // Map unified props to FIMessageBubble props
  const bubbleProps: FIMessageBubbleProps = {
    message,
    showTimestamp,
    showSenderName,
    animate,
    className,
    borderRadiusOverride,
  };

  return <FIMessageBubble {...bubbleProps} />;
}

/**
 * Re-export FIMessageBubble types for convenience
 */
export type { FIMessageBubbleProps };
