import type { CatalogSource, LLMProvider } from './types';

export type ProviderOrSource = LLMProvider | CatalogSource | (string & {});

export interface ProviderLogoProps {
  provider: ProviderOrSource;
  size?: number;
  className?: string;
}

const STROKE = { stroke: 'currentColor', strokeWidth: 1.5, strokeLinecap: 'round' as const };

export function ProviderLogo({ provider, size = 24, className }: ProviderLogoProps) {
  const svg = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', className, 'aria-hidden': true };
  switch (provider) {
    case 'openai':
      return (
        <svg {...svg}>
          <path d="M12 2L3 7v10l9 5 9-5V7l-9-5z" stroke="currentColor" strokeWidth={1.5} />
          <circle cx="12" cy="12" r="3" fill="currentColor" />
          <path d="M12 5v4M12 15v4M5.5 8.5l3.5 2M15 13.5l3.5 2M5.5 15.5l3.5-2M15 10.5l3.5-2" {...STROKE} />
        </svg>
      );
    case 'anthropic':
      return (
        <svg {...svg}>
          <path d="M12 3L4 21h3.5l1.5-4h6l1.5 4H20L12 3z" fill="currentColor" />
        </svg>
      );
    case 'azure':
      return (
        <svg {...svg}>
          <path d="M6.5 19a4.5 4.5 0 01-.5-8.97 5.5 5.5 0 0110.74-1.52A4 4 0 0118.5 16h-.5" {...STROKE} strokeLinejoin="round" />
          <path d="M6 19h12" {...STROKE} />
        </svg>
      );
    case 'ollama':
      return (
        <svg {...svg}>
          <path
            d="M12 4c-2 0-3.5 1-4.5 2.5C6.5 8 6 9.5 6 11v6c0 1.5.5 2 2 2.5.5.2 1 .3 1.5.4M12 4c2 0 3.5 1 4.5 2.5 1 1.5 1.5 3 1.5 4.5v6c0 1.5-.5 2-2 2.5-.5.2-1 .3-1.5.4"
            {...STROKE}
          />
          <circle cx="9" cy="10" r="1" fill="currentColor" />
          <circle cx="15" cy="10" r="1" fill="currentColor" />
          <path d="M6 7c-1-1-2-1-3 0M18 7c1-1 2-1 3 0" {...STROKE} />
          <ellipse cx="12" cy="14" rx="2" ry="1.5" stroke="currentColor" strokeWidth={1} />
        </svg>
      );
    case 'gpt4all':
      return (
        <svg {...svg}>
          <path d="M12 22V12" {...STROKE} />
          <path d="M12 12c-4-2-6-6-5-10 4 1 7 4 8 8" {...STROKE} strokeLinejoin="round" />
          <path d="M12 12c4-2 6-6 5-10-4 1-7 4-8 8" {...STROKE} strokeLinejoin="round" />
          <path d="M12 16c-2 0-4 1-5 3M12 16c2 0 4 1 5 3" {...STROKE} />
        </svg>
      );
    case 'huggingface':
      return (
        <svg {...svg}>
          <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth={1.5} />
          <circle cx="9" cy="10" r="1.5" fill="currentColor" />
          <circle cx="15" cy="10" r="1.5" fill="currentColor" />
          <path d="M8 14c1 2 3 3 4 3s3-1 4-3" {...STROKE} />
          <path d="M3 10c0 2 1 4 2 5M21 10c0 2-1 4-2 5" {...STROKE} />
        </svg>
      );
    default:
      return (
        <svg {...svg}>
          <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth={1.5} />
          <path d="M12 8v8M8 12h8" {...STROKE} />
        </svg>
      );
  }
}

/** The logo inside a tinted box; the tint follows the provider via `data-provider`. */
export function ProviderLogoBox({ provider, size = 28, className }: ProviderLogoProps) {
  return (
    <span className={className ? `fi-mc-logo ${className}` : 'fi-mc-logo'} data-provider={provider}>
      <ProviderLogo provider={provider} size={size} />
    </span>
  );
}
