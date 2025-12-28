'use client';

import { memo } from 'react';
import type { AISuggestion } from '../types';
import { getSuggestionStyles } from '../utils';

interface AISuggestionCardProps {
  suggestion: AISuggestion;
}

export const AISuggestionCard = memo(function AISuggestionCard({
  suggestion,
}: AISuggestionCardProps) {
  const styles = getSuggestionStyles(suggestion.type);
  const Icon = styles.icon;

  const typeLabels: Record<AISuggestion['type'], string> = {
    warning: 'Advertencia',
    suggestion: 'Sugerencia',
    insight: 'Insight',
  };

  return (
    <div className={`rounded-lg p-3 border ${styles.bg} ${styles.border}`}>
      <div className="flex items-start gap-2">
        <Icon
          className={`h-4 w-4 ${styles.text} mt-0.5 flex-shrink-0`}
          aria-hidden="true"
        />
        <div>
          <p className={`text-sm font-medium ${styles.text}`}>
            {typeLabels[suggestion.type]}
          </p>
          <p className={`text-xs mt-1 ${styles.text.replace('-400', '-300')}`}>
            {suggestion.content}
          </p>
          <p className="fi-text-xs mt-1">
            Confianza: {Math.round(suggestion.confidence * 100)}% •{' '}
            {suggestion.source}
          </p>
        </div>
      </div>
    </div>
  );
});
