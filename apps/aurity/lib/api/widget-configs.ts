/**
 * Widget Configurations API Client
 *
 * Client functions for managing configurable TV widgets
 * (trivia, breathing exercises, daily tips)
 *
 * Card: FI-TV-REFAC-003
 */

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://app.aurity.io';

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

  const url = `${BACKEND_URL}/api/workflows/aurity/widget-config/trivia${
    queryParams.toString() ? `?${queryParams}` : ''
  }`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch trivia: ${response.status}`);
  }

  return response.json();
}

/**
 * Save trivia question to config
 * Note: This requires backend endpoint for saving (to be implemented)
 */
export async function saveTriviaQuestion(question: TriviaQuestion): Promise<{ success: boolean }> {
  // For now, this would need to update the JSON file via backend
  // Backend endpoint: POST /api/workflows/aurity/widget-config/trivia

  const response = await fetch(`${BACKEND_URL}/api/workflows/aurity/widget-config/trivia`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(question),
  });

  if (!response.ok) {
    throw new Error(`Failed to save trivia: ${response.status}`);
  }

  return response.json();
}

/**
 * Delete trivia question from config
 */
export async function deleteTriviaQuestion(questionId: string): Promise<{ success: boolean }> {
  const response = await fetch(
    `${BACKEND_URL}/api/workflows/aurity/widget-config/trivia/${questionId}`,
    { method: 'DELETE' }
  );

  if (!response.ok) {
    throw new Error(`Failed to delete trivia: ${response.status}`);
  }

  return response.json();
}

/**
 * Get breathing exercises from config
 */
export async function getBreathingExercises(params?: {
  exercise_id?: string;
}): Promise<BreathingConfigResponse> {
  const queryParams = new URLSearchParams();
  if (params?.exercise_id) queryParams.append('exercise_id', params.exercise_id);

  const url = `${BACKEND_URL}/api/workflows/aurity/widget-config/breathing${
    queryParams.toString() ? `?${queryParams}` : ''
  }`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch breathing exercises: ${response.status}`);
  }

  return response.json();
}

/**
 * Get daily health tips from config
 */
export async function getDailyTips(params?: {
  category?: 'nutrition' | 'exercise' | 'mental_health' | 'prevention';
}): Promise<TipsConfigResponse> {
  const queryParams = new URLSearchParams();
  if (params?.category) queryParams.append('category', params.category);

  const url = `${BACKEND_URL}/api/workflows/aurity/widget-config/daily-tips${
    queryParams.toString() ? `?${queryParams}` : ''
  }`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch daily tips: ${response.status}`);
  }

  return response.json();
}

/**
 * Get a random daily tip
 */
export async function getRandomTip(params?: {
  category?: 'nutrition' | 'exercise' | 'mental_health' | 'prevention';
}): Promise<HealthTip> {
  const queryParams = new URLSearchParams();
  if (params?.category) queryParams.append('category', params.category);

  const url = `${BACKEND_URL}/api/workflows/aurity/widget-config/random-tip${
    queryParams.toString() ? `?${queryParams}` : ''
  }`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch random tip: ${response.status}`);
  }

  return response.json();
}
