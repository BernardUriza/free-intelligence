/**
 * Content API Service
 * Fetches content seeds, dynamic tips, and trivia from backend
 */

import { contentCache } from './content-cache';
import type { ContentItem } from '../types';
import { waitingRoomAPI, type TipCategory } from '@/lib/api/waiting-room';
import { api, getBackendUrl } from '@/lib/api/client';

/**
 * Fetch FI content seeds from backend API
 * Replaces hardcoded DEFAULT_CONTENT with editable seeds from DB
 */
export async function fetchContentSeeds(): Promise<ContentItem[]> {
  try {
    const data = await api.get<{ content: Record<string, unknown>[] }>(
      '/api/aurity/clinic/tv-content/list?active_only=true'
    );

    // Convert TVContentSeed[] to ContentItem[]
    const seeds: ContentItem[] = data.content.map((seed: Record<string, unknown>) => ({
      type: seed.type as ContentItem['type'],
      content: seed.content as string,
      duration: seed.duration as number | undefined,
      widgetType: seed.widget_type as ContentItem['widgetType'],
      widgetData: seed.widget_data as Record<string, unknown> | undefined,
      metadata: {
        content_id: seed.content_id,
        is_system_default: seed.is_system_default,
        display_order: seed.display_order,
      },
    }));

    return seeds;
  } catch (error) {
    console.error('Failed to fetch content seeds, using fallback:', error);

    // Fallback to minimal static content if API fails
    return [
      {
        type: 'welcome',
        content:
          'Bienvenidos a nuestra clínica. Free Intelligence está aquí para acompañarlos durante su espera.',
        duration: 12000,
      },
      {
        type: 'tip',
        content:
          '💧 **Tip de Salud**: Mantenerse hidratado es esencial. Beba al menos 8 vasos de agua al día para una salud óptima.',
        duration: 15000,
      },
    ];
  }
}

/**
 * Fetch a dynamic health tip with caching
 */
export async function fetchDynamicTip(category: TipCategory): Promise<string> {
  const cacheKey = `tip_${category}`;

  // Check cache first
  const cached = contentCache.get<string>(cacheKey);
  if (cached) {
    return cached;
  }

  // Fetch from API
  try {
    const response = await waitingRoomAPI.generateTip({ category });
    const tip = response.tip;

    // Cache for 30 minutes
    contentCache.set(cacheKey, tip, 30 * 60 * 1000);

    return tip;
  } catch (error) {
    console.error('Failed to fetch dynamic tip:', error);
    // Fallback to static content
    return 'Mantenerse activo y comer balanceado son pilares de una vida saludable.';
  }
}

/**
 * Trivia data structure
 */
export interface TriviaData {
  question: string;
  options: string[];
  correctAnswer: number;
  explanation: string;
}

/**
 * Fetch a dynamic trivia question with caching
 */
export async function fetchDynamicTrivia(): Promise<TriviaData> {
  const cacheKey = 'trivia_easy';

  // Check cache first
  const cached = contentCache.get<TriviaData>(cacheKey);
  if (cached) {
    return cached;
  }

  // Fetch from API
  try {
    const response = await waitingRoomAPI.generateTrivia({ difficulty: 'easy' });

    const triviaData: TriviaData = {
      question: response.question,
      options: response.options,
      correctAnswer: response.correct_answer,
      explanation: response.explanation,
    };

    // Cache for 30 minutes
    contentCache.set(cacheKey, triviaData, 30 * 60 * 1000);

    return triviaData;
  } catch (error) {
    console.error('Failed to fetch dynamic trivia:', error);
    // Fallback to static content
    return {
      question: '¿Cuántos vasos de agua se recomienda beber al día?',
      options: ['4-5 vasos', '6-7 vasos', '8-10 vasos', '12-15 vasos'],
      correctAnswer: 2,
      explanation:
        'Se recomienda beber entre 8 y 10 vasos de agua al día para mantener una hidratación adecuada.',
    };
  }
}

/**
 * Build media URL from file path
 */
export function buildMediaUrl(filePath: string): string {
  return `${getBackendUrl()}/api/aurity/clinic/clinic-media/file/${filePath}`;
}
