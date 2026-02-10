/**
 * Widget Configurations API Client
 *
 * Client functions for managing configurable TV widgets
 * (trivia, breathing exercises, daily tips)
 *
 * Card: FI-TV-REFAC-003
 */

import { api } from './client';
import { ROUTES } from './routes';

const API_BASE = ROUTES.widgetConfig;

// ============================================================================
// Type Definitions
// ============================================================================

export interface TriviaQuestion {
  id: string;
  question: string;
  options: string[];
  correct: number;
  explanation: string;
  difficulty: 'easy' | 'medium' | 'hard';
  category: string;
  tags: string[];
}

export interface BreathingPhase {
  phase: 'inhale' | 'hold' | 'exhale';
  duration: number;
  label: string;
  icon: string;
  color: 'cyan' | 'purple' | 'orange' | 'green' | 'blue';
}

export interface BreathingExercise {
  id: string;
  name: string;
  description: string;
  pattern: BreathingPhase[];
  total_duration: number;
  benefits: string[];
  difficulty: 'beginner' | 'intermediate' | 'advanced';
}

export interface HealthTip {
  id: string;
  tip: string;
  icon: string;
  source: string;
  tags: string[];
}

export interface TriviaConfigResponse {
  total_questions: number;
  questions: TriviaQuestion[];
}

export interface BreathingConfigResponse {
  total_exercises: number;
  exercises: BreathingExercise[];
  default_exercise: string;
}

export interface TipsConfigResponse {
  tips_by_category: Record<string, HealthTip[]>;
  total_tips: number;
  categories: string[];
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Get trivia questions from config
 */
export async function getTriviaQuestions(params?: {
  difficulty?: 'easy' | 'medium' | 'hard';
  limit?: number;
}): Promise<TriviaConfigResponse> {
  const queryParams = new URLSearchParams();
  if (params?.difficulty) queryParams.append('difficulty', params.difficulty);
  if (params?.limit) queryParams.append('limit', params.limit.toString());

  const query = queryParams.toString() ? `?${queryParams}` : '';
  return api.get<TriviaConfigResponse>(`${API_BASE}/trivia${query}`);
}

/**
 * Save trivia question to config
 * Note: This requires backend endpoint for saving (to be implemented)
 */
export async function saveTriviaQuestion(question: TriviaQuestion): Promise<{ success: boolean }> {
  return api.post<{ success: boolean }>(`${API_BASE}/trivia`, question);
}

/**
 * Delete trivia question from config
 */
export async function deleteTriviaQuestion(questionId: string): Promise<{ success: boolean }> {
  return api.delete<{ success: boolean }>(`${API_BASE}/trivia/${questionId}`);
}

/**
 * Get breathing exercises from config
 */
export async function getBreathingExercises(params?: {
  exercise_id?: string;
}): Promise<BreathingConfigResponse> {
  const queryParams = new URLSearchParams();
  if (params?.exercise_id) queryParams.append('exercise_id', params.exercise_id);

  const query = queryParams.toString() ? `?${queryParams}` : '';
  return api.get<BreathingConfigResponse>(`${API_BASE}/breathing${query}`);
}

/**
 * Get daily health tips from config
 */
export async function getDailyTips(params?: {
  category?: 'nutrition' | 'exercise' | 'mental_health' | 'prevention';
}): Promise<TipsConfigResponse> {
  const queryParams = new URLSearchParams();
  if (params?.category) queryParams.append('category', params.category);

  const query = queryParams.toString() ? `?${queryParams}` : '';
  return api.get<TipsConfigResponse>(`${API_BASE}/daily-tips${query}`);
}

/**
 * Get a random daily tip
 */
export async function getRandomTip(params?: {
  category?: 'nutrition' | 'exercise' | 'mental_health' | 'prevention';
}): Promise<HealthTip> {
  const queryParams = new URLSearchParams();
  if (params?.category) queryParams.append('category', params.category);

  const query = queryParams.toString() ? `?${queryParams}` : '';
  return api.get<HealthTip>(`${API_BASE}/random-tip${query}`);
}
