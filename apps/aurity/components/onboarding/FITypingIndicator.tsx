/**
 * FITypingIndicator Component
 *
 * Card: FI-ONBOARD-002
 * Animated typing indicator for Free-Intelligence
 */

export interface FITypingIndicatorProps {
  /** Show typing indicator */
  show?: boolean;

  /** Persona for styling (optional) */
  persona?: 'onboarding_guide' | 'general_assistant' | 'clinical_advisor' | 'soap_editor';

  /** Additional CSS classes */
  className?: string;
}

/**
 * Typing indicator for Free-Intelligence
 *
 * Shows animated dots when FI is "thinking"
 *
 * Features:
 * - Smooth fade in/out
 * - Bouncing dots animation
 * - Persona-based color theming
 * - Accessible ARIA labels
 *
 * @example
 * ```tsx
 * {isTyping && (
 *   <FITypingIndicator
 *     show
 *     persona="onboarding_guide"
 *   />
 * )}
 * ```
 */
export function FITypingIndicator({
  show = true,
  persona = 'general_assistant',
  className = '',
}: FITypingIndicatorProps) {
  if (!show) {
    return null;
  }

  // Persona-based dot colors
  const dotColors = {
    onboarding_guide: 'bg-emerald-400',
    general_assistant: 'bg-slate-400',
    clinical_advisor: 'bg-blue-400',
    soap_editor: 'bg-cyan-400',
  };

  const dotColor = dotColors[persona] || dotColors.general_assistant;

  return (
    <div
      className={`flex items-start gap-3 animate-fade-in ${className}`}
      role="status"
      aria-live="polite"
      aria-label="Free-Intelligence is typing"
    >
      {/* Typing Bubble */}
      <div className="fi-typing-bubble">
        {/* Animated Dots */}
        <div className="fi-flex-gap-sm">
          <div className={`fi-typing-dot ${dotColor} animation-delay-0`} />
          <div className={`fi-typing-dot ${dotColor} animation-delay-150`} />
          <div className={`fi-typing-dot ${dotColor} animation-delay-300`} />
        </div>
      </div>

      {/* Screen reader text */}
      <span className="sr-only">Free-Intelligence está escribiendo...</span>
    </div>
  );
}

/**
 * Animation CSS (add to globals.css or Tailwind config)
 *
 * @keyframes bounce-dot {
 *   0%, 60%, 100% {
 *     transform: translateY(0);
 *     opacity: 0.7;
 *   }
 *   30% {
 *     transform: translateY(-8px);
 *     opacity: 1;
 *   }
 * }
 *
 * @keyframes fade-in {
 *   from {
 *     opacity: 0;
 *   }
 *   to {
 *     opacity: 1;
 *   }
 * }
 *
 * .animate-bounce-dot {
 *   animation: bounce-dot 1.4s ease-in-out infinite;
 * }
 *
 * .animation-delay-0 {
 *   animation-delay: 0ms;
 * }
 *
 * .animation-delay-150 {
 *   animation-delay: 150ms;
 * }
 *
 * .animation-delay-300 {
 *   animation-delay: 300ms;
 * }
 *
 * .animate-fade-in {
 *   animation: fade-in 0.3s ease-out;
 * }
 */
