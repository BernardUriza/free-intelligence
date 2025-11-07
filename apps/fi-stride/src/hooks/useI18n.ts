/**
 * i18n Hook - Access translations with templating support
 *
 * Usage:
 * ```tsx
 * const t = useI18n();
 * t('session.title')  // Returns: "Sesión de Entrenamiento"
 * t('reps.completed_many', { count: 5 })  // Returns: "5 repeticiones completadas"
 * ```
 */

import { useMemo } from 'react';
import { useTheme } from './useTheme';
import liveI18n from '../i18n/live.json';

type Language = 'es' | 'en';
type TranslationKey = string;

interface TemplateParams {
  [key: string]: string | number;
}

/**
 * Get nested value from object using dot notation
 */
function getNestedValue(obj: any, path: string): string | undefined {
  const keys = path.split('.');
  let value = obj;

  for (const key of keys) {
    if (value && typeof value === 'object' && key in value) {
      value = value[key];
    } else {
      return undefined;
    }
  }

  return typeof value === 'string' ? value : undefined;
}

/**
 * Replace template variables in translation string
 */
function interpolate(template: string, params: TemplateParams): string {
  return template.replace(/\{(\w+)\}/g, (match, key) => {
    const value = params[key];
    return value !== undefined ? String(value) : match;
  });
}

/**
 * useI18n Hook
 */
export function useI18n() {
  // Default to Spanish, could be based on locale/context
  const language: Language = 'es';

  const translations = useMemo(() => {
    return liveI18n[language] || liveI18n['es'];
  }, [language]);

  /**
   * Translate key with optional template parameters
   */
  const t = (key: TranslationKey, params?: TemplateParams): string => {
    const value = getNestedValue(translations, key);

    if (!value) {
      console.warn(`Translation missing: ${language}.${key}`);
      return key; // Fallback to key name
    }

    if (params) {
      return interpolate(value, params);
    }

    return value;
  };

  return t;
}

export type { Language, TranslationKey, TemplateParams };
