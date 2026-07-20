/**
 * fi-glass · FloatingButton — the closed-state launcher (bottom-right).
 * Pure: lucide icon + app CSS classes (fi-fab-emerald, fi-dot-pulse-red,
 * fi-tooltip-right live in the app's stylesheet). Copied verbatim from aurity.
 */

import { MessageCircle } from 'lucide-react';

export interface FloatingButtonProps {
  onClick: () => void;
  isMobile: boolean;
}

export function FloatingButton({ onClick, isMobile }: FloatingButtonProps) {
  const buttonSize = isMobile ? 'w-16 h-16' : 'w-14 h-14';
  const iconSize = isMobile ? 'h-7 w-7' : 'h-6 w-6';
  const buttonPosition = isMobile ? 'bottom-4 right-4' : 'bottom-6 right-6';

  return (
    <button
      onClick={onClick}
      className={`
        fixed ${buttonPosition} ${buttonSize}
        fi-fab-emerald z-50 group
      `}
      aria-label="Chat with Free Intelligence"
    >
      <MessageCircle className={`${iconSize} text-white`} />

      {/* Notification badge */}
      <span className="fi-dot-pulse-red" />

      {/* Tooltip (hide on mobile) */}
      {!isMobile && (
        <div className="fi-tooltip-right">
          Habla con Free Intelligence
        </div>
      )}
    </button>
  );
}
