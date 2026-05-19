/**
 * Waiting Room Content API Client
 *
 * Card: FI-UI-FEAT-TVD-001
 * HTTP client for dynamic content generation for waiting room TV displays
 *
 * Updated: 2026-02 - Migrated to centralized api client
 */

import { api } from './client';
import { ROUTES } from './routes';

// ============================================================================
// Types
// ============================================================================

export type TipCategory = 'nutrition' | 'exercise' | 'mental_health' | 'prevention';
export type TriviaDifficulty = 'easy' | 'medium' | 'hard';

export interface GenerateTipRequest {
  category: TipCategory;
  context?: string;
}

export interface GenerateTipResponse {
  tip: string;
  category: string;
  generated_by: string;
  tokens_used: number;
  latency_ms: number;
}

export interface GenerateTriviaRequest {
  difficulty?: TriviaDifficulty;
}

export interface GenerateTriviaResponse {
  question: string;
  options: string[];
  correct_answer: number;
  explanation: string;
  tokens_used: number;
  latency_ms: number;
}

// ============================================================================
// API Functions
// ============================================================================

const API_BASE = ROUTES.waitingRoom;

/**
 * Generate a health tip using Free Intelligence
 *
 * @example
 * ```ts
 * const tip = await generateTip({ category: 'nutrition', context: 'morning' });
 * console.log(tip.tip); // "Incluir frutas en el desayuno..."
 * ```
 */
export async function generateTip(request: GenerateTipRequest): Promise<GenerateTipResponse> {
  return api.post<GenerateTipResponse>(`${API_BASE}/generate-tip`, request, {
    timeout: 10000, // 10s for LLM generation
  });
}

/**
 * Generate a health trivia question using Free Intelligence
 *
 * @example
 * ```ts
 * const trivia = await generateTrivia({ difficulty: 'easy' });
 * console.log(trivia.question);
 * console.log(trivia.options); // ["A", "B", "C", "D"]
 * ```
 */
export async function generateTrivia(request: GenerateTriviaRequest = {}): Promise<GenerateTriviaResponse> {
  return api.post<GenerateTriviaResponse>(`${API_BASE}/generate-trivia`, request, {
    timeout: 10000, // 10s for LLM generation
  });
}

