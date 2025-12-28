'use client';

/**
 * LoadMoreButton - Single Responsibility: Pagination trigger
 *
 * SOLID Principles:
 * - S: Only handles "load more" action display and trigger
 * - O: Extensible via className and custom loading content
 * - I: Minimal props interface
 */

import { memo } from 'react';
import { ChevronUp, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface LoadMoreButtonProps {
  onLoadMore: () => void;
  isLoading: boolean;
  loadingText?: string;
  buttonText?: string;
  className?: string;
}

export const LoadMoreButton = memo(function LoadMoreButton({
  onLoadMore,
  isLoading,
  loadingText = 'Cargando...',
  buttonText = 'Cargar mensajes anteriores',
  className = '',
}: LoadMoreButtonProps) {
  return (
    <div className={`chat-load-more ${className}`}>
      <Button
        onClick={onLoadMore}
        disabled={isLoading}
        className="chat-load-more-btn"
        aria-label={isLoading ? loadingText : buttonText}
        variant="ghost"
        size="sm"
        type="button"
      >
        {isLoading ? (
          <>
            <Loader2 className="fi-icon-xs animate-spin" />
            {loadingText}
          </>
        ) : (
          <>
            <ChevronUp className="fi-icon-xs" />
            {buttonText}
          </>
        )}
      </Button>
    </div>
  );
});
