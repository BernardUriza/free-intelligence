/**
 * ClinicalNotes Utilities
 */

import { AlertTriangle, CheckCircle2, Brain } from 'lucide-react';
import type { AISuggestion, SuggestionStyles } from './types';

export function getSeverityStyles(severity: string | undefined): string {
  switch (severity) {
    case 'Leve':
      return 'cnotes-severity-leve';
    case 'Moderada':
      return 'cnotes-severity-moderada';
    default:
      return 'cnotes-severity-default';
  }
}

export function getSuggestionStyles(type: AISuggestion['type']): SuggestionStyles {
  switch (type) {
    case 'warning':
      return {
        bg: 'bg-red-500/10',
        border: 'border-red-500/30',
        text: 'text-red-400',
        icon: AlertTriangle,
      };
    case 'suggestion':
      return {
        bg: 'bg-blue-500/10',
        border: 'border-blue-500/30',
        text: 'text-blue-400',
        icon: CheckCircle2,
      };
    default:
      return {
        bg: 'bg-emerald-500/10',
        border: 'border-emerald-500/30',
        text: 'fi-text-success',
        icon: Brain,
      };
  }
}
