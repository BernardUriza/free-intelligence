/**
 * ProviderLogo Component
 *
 * SVG logos for LLM providers. Minimal, distinctive icons.
 */

import type { LLMProvider } from '@aurity-standalone/types/llm';

interface ProviderLogoProps {
  provider: LLMProvider | string;
  size?: number;
  className?: string;
}

export function ProviderLogo({ provider, size = 24, className = '' }: ProviderLogoProps) {
  const svgProps = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    className,
  };

  switch (provider) {
    case 'openai':
      // OpenAI - Hexagonal/neural network inspired shape
      return (
        <svg {...svgProps}>
          <path
            d="M12 2L3 7v10l9 5 9-5V7l-9-5z"
            stroke="currentColor"
            strokeWidth="1.5"
            fill="none"
          />
          <circle cx="12" cy="12" r="3" fill="currentColor" />
          <path
            d="M12 5v4M12 15v4M5.5 8.5l3.5 2M15 13.5l3.5 2M5.5 15.5l3.5-2M15 10.5l3.5-2"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      );

    case 'anthropic':
      // Anthropic Claude - Abstract "A" shape
      return (
        <svg {...svgProps}>
          <path
            d="M12 3L4 21h3.5l1.5-4h6l1.5 4H20L12 3z"
            fill="currentColor"
          />
          <path
            d="M9.5 14l2.5-7 2.5 7"
            stroke="currentColor"
            strokeWidth="0"
          />
        </svg>
      );

    case 'azure':
      // Microsoft Azure - Cloud shape
      return (
        <svg {...svgProps}>
          <path
            d="M6.5 19a4.5 4.5 0 01-.5-8.97 5.5 5.5 0 0110.74-1.52A4 4 0 0118.5 16h-.5"
            stroke="currentColor"
            strokeWidth="1.5"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M6 19h12"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      );

    case 'ollama':
      // Ollama - Llama head silhouette (local/self-hosted)
      return (
        <svg {...svgProps}>
          <path
            d="M12 4c-2 0-3.5 1-4.5 2.5C6.5 8 6 9.5 6 11v6c0 1.5.5 2 2 2.5.5.2 1 .3 1.5.4M12 4c2 0 3.5 1 4.5 2.5 1 1.5 1.5 3 1.5 4.5v6c0 1.5-.5 2-2 2.5-.5.2-1 .3-1.5.4"
            stroke="currentColor"
            strokeWidth="1.5"
            fill="none"
            strokeLinecap="round"
          />
          <circle cx="9" cy="10" r="1" fill="currentColor" />
          <circle cx="15" cy="10" r="1" fill="currentColor" />
          <path
            d="M6 7c-1-1-2-1-3 0M18 7c1-1 2-1 3 0"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <ellipse cx="12" cy="14" rx="2" ry="1.5" stroke="currentColor" strokeWidth="1" fill="none" />
        </svg>
      );

    default:
      // Generic AI/Brain icon for unknown providers
      return (
        <svg {...svgProps}>
          <circle
            cx="12"
            cy="12"
            r="9"
            stroke="currentColor"
            strokeWidth="1.5"
            fill="none"
          />
          <path
            d="M12 8v8M8 12h8"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      );
  }
}

// Wrapper with background for card usage
export function ProviderLogoBox({
  provider,
  size = 32,
  className = ''
}: ProviderLogoProps) {
  const colorMap: Record<string, string> = {
    openai: 'bg-emerald-900/50 border-emerald-700/50 fi-text-success',
    anthropic: 'bg-orange-900/50 border-orange-700/50 text-orange-400',
    azure: 'bg-blue-900/50 border-blue-700/50 fi-text-primary',
    ollama: 'bg-slate-800/50 border-slate-600/50 fi-text',
  };

  const colorClass = colorMap[provider] || 'bg-slate-800/50 border-slate-600/50 text-slate-400';

  return (
    <div className={`p-2 rounded-lg border ${colorClass} ${className}`}>
      <ProviderLogo provider={provider} size={size} />
    </div>
  );
}
