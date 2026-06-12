'use client';

/**
 * fi-glass · ScrollToBottomButton — the floating "jump to latest" affordance.
 *
 * Rendered by AgentConversationSurface when the user has scrolled away from the
 * bottom (the industry pattern: ChatGPT's 32px round chevron, AI Elements'
 * ConversationScrollButton). Position is framework-owned (absolute, centered
 * above the composer); the skin is consumer-overridable via `className` — the
 * structural placement survives the override so a consumer can't accidentally
 * detach the button from its anchor.
 */

import type { CSSProperties } from 'react';
import { ChevronDown } from 'lucide-react';

export interface ScrollToBottomButtonProps {
  onClick: () => void;
  /** Accessible label. Default: "Ir al final". */
  label?: string;
  /** Visual class. When set, the default skin is dropped (placement stays). */
  className?: string;
  /** Icon class. */
  iconClassName?: string;
}

// Placement is structural and always applied; skin only when no className.
const placement: CSSProperties = {
  position: 'absolute',
  bottom: 12,
  left: '50%',
  transform: 'translateX(-50%)',
};

const skin: CSSProperties = {
  width: 32,
  height: 32,
  borderRadius: 9999,
  border: '1px solid rgba(255,255,255,0.15)',
  background: 'rgba(15,23,42,0.85)',
  color: '#e2e8f0',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  backdropFilter: 'blur(4px)',
  WebkitBackdropFilter: 'blur(4px)',
  boxShadow: '0 2px 8px rgba(0,0,0,0.35)',
};

export function ScrollToBottomButton({
  onClick,
  label = 'Ir al final',
  className,
  iconClassName,
}: ScrollToBottomButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      // fi-scroll-to-bottom is always present: glass-chat.css hangs the
      // :focus-visible ring off it (inline styles can't express focus states).
      className={className ? `fi-scroll-to-bottom ${className}` : 'fi-scroll-to-bottom'}
      style={className ? placement : { ...placement, ...skin }}
    >
      <ChevronDown size={16} className={iconClassName} aria-hidden />
    </button>
  );
}
