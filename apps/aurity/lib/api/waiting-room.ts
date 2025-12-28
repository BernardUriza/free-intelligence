/**
 * Waiting Room Content API Client
 *
 * Card: FI-UI-FEAT-TVD-001
 * HTTP client for dynamic content generation for waiting room TV displays
 */

/**
 * API Request/Response Types
 */
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

/**
 * API configuration
 */
interface WaitingRoomAPIConfig {
  baseURL: string;
  timeout?: number;
  maxRetries?: number;
  retryDelay?: number;
}

/**
 * Default configuration
 */
const DEFAULT_CONFIG: Required<WaitingRoomAPIConfig> = {
  baseURL: process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001',
  timeout: 10000, // 10 seconds (content generation can take 2-5s)
  maxRetries: 2,
  retryDelay: 1000, // 1 second
};

/**
 * Retry-able HTTP fetch with exponential backoff
 */
async function fetchWithRetry(
  url: string,
  options: RequestInit,
  config: Required<WaitingRoomAPIConfig>
): Promise<Response> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt < config.maxRetries; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), config.timeout);

      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Don't retry on 4xx client errors
      if (!response.ok && response.status >= 400 && response.status < 500) {
        const error = await response.json();
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      // Retry on 5xx server errors
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return response;
    } catch (error) {
      lastError = error as Error;

      // Don't retry on timeout
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`Request timeout after ${config.timeout}ms`);
      }

      // Don't retry on last attempt
      if (attempt === config.maxRetries - 1) {
        break;
      }

      // Exponential backoff
      const delay = config.retryDelay * Math.pow(2, attempt);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw lastError || new Error('Unknown error during fetch');
}

/**
 * Waiting Room Content API Client
 */
export class WaitingRoomAPI {
  private config: Required<WaitingRoomAPIConfig>;

  constructor(config?: Partial<WaitingRoomAPIConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Generate a health tip using Free Intelligence
   *
   * Endpoint: POST /api/workflows/aurity/waiting-room/generate-tip
   *
   * @param request Tip generation request (category + optional context)
   * @returns Generated tip with metadata
   * @throws Error if request fails
   *
   * @example
   * ```ts
   * const api = new WaitingRoomAPI();
   * const tip = await api.generateTip({
   *   category: 'nutrition',
   *   context: 'morning'
   * });
   * console.log(tip.tip); // "Incluir frutas en el desayuno..."
   * console.log(tip.latency_ms); // 4634
   * ```
   */
  async generateTip(request: GenerateTipRequest): Promise<GenerateTipResponse> {
    const url = `${this.config.baseURL}/api/workflows/aurity/waiting-room/generate-tip`;

    const response = await fetchWithRetry(
      url,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      },
      this.config
    );

    const data: GenerateTipResponse = await response.json();
    return data;
  }

  /**
   * Generate a health trivia question using Free Intelligence
   *
   * Endpoint: POST /api/workflows/aurity/waiting-room/generate-trivia
   *
   * @param request Trivia generation request (difficulty level)
   * @returns Generated trivia question with options and explanation
   * @throws Error if request fails
   *
   * @example
   * ```ts
   * const api = new WaitingRoomAPI();
   * const trivia = await api.generateTrivia({ difficulty: 'easy' });
   * console.log(trivia.question);
   * console.log(trivia.options); // ["A", "B", "C", "D"]
   * console.log(trivia.correct_answer); // 2
   * console.log(trivia.explanation);
   * ```
   */
  async generateTrivia(request: GenerateTriviaRequest = {}): Promise<GenerateTriviaResponse> {
    const url = `${this.config.baseURL}/api/workflows/aurity/waiting-room/generate-trivia`;

    const response = await fetchWithRetry(
      url,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      },
      this.config
    );

    const data: GenerateTriviaResponse = await response.json();
    return data;
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<WaitingRoomAPIConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Get current configuration
   */
  getConfig(): Readonly<Required<WaitingRoomAPIConfig>> {
    return { ...this.config };
  }
}

/**
 * Singleton instance for convenience
 */
export const waitingRoomAPI = new WaitingRoomAPI();
