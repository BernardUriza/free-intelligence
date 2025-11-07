/**
 * Free Intelligence - API Client
 *
 * TypeScript client for FI Consult Service (port 7001)
 */

import {
  StartConsultationRequest,
  StartConsultationResponse,
  AppendEventRequest,
  AppendEventResponse,
  GetConsultationResponse,
  GetSOAPResponse,
  GetEventsResponse,
} from '../models/consultation';

export interface FIClientConfig {
  baseUrl: string; // e.g., "http://localhost:7001"
  timeout?: number; // milliseconds
  headers?: Record<string, string>;
}

export class FIClient {
  private config: Required<FIClientConfig>;

  constructor(config: FIClientConfig) {
    this.config = {
      baseUrl: config.baseUrl.replace(/\/$/, ''), // Remove trailing slash
      timeout: config.timeout || 30000,
      headers: config.headers || {},
    };
  }

  /**
   * Start a new consultation
   */
  async startConsultation(
    request: StartConsultationRequest
  ): Promise<StartConsultationResponse> {
    return this.post<StartConsultationResponse>('/consultations', request);
  }

  /**
   * Append an event to a consultation
   */
  async appendEvent(
    consultationId: string,
    request: AppendEventRequest
  ): Promise<AppendEventResponse> {
    return this.post<AppendEventResponse>(
      `/consultations/${consultationId}/events`,
      request
    );
  }

  /**
   * Get consultation state (reconstructed from events)
   */
  async getConsultation(consultationId: string): Promise<GetConsultationResponse> {
    return this.get<GetConsultationResponse>(`/consultations/${consultationId}`);
  }

  /**
   * Get SOAP note
   */
  async getSOAP(consultationId: string): Promise<GetSOAPResponse> {
    return this.get<GetSOAPResponse>(`/consultations/${consultationId}/soap`);
  }

  /**
   * Get event stream
   */
  async getEvents(consultationId: string): Promise<GetEventsResponse> {
    return this.get<GetEventsResponse>(`/consultations/${consultationId}/events`);
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string; service: string }> {
    return this.get('/health');
  }

  /**
   * Generic GET request
   */
  private async get<T>(path: string): Promise<T> {
    const url = `${this.config.baseUrl}${path}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...this.config.headers,
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const error = await response.json().catch(() => ({})) as Record<string, unknown>;
        throw new FIClientError(
          response.status,
          (error?.detail as string) || response.statusText,
          error
        );
      }

      return response.json() as Promise<T>;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof FIClientError) {
        throw error;
      }
      if (error instanceof Error && error.name === 'AbortError') {
        throw new FIClientError(408, 'Request timeout', { timeout: this.config.timeout });
      }
      throw new FIClientError(0, 'Network error', { originalError: error });
    }
  }

  /**
   * Generic POST request
   */
  private async post<T>(path: string, data: unknown): Promise<T> {
    const url = `${this.config.baseUrl}${path}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.config.headers,
        },
        body: JSON.stringify(data),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const error = await response.json().catch(() => ({})) as Record<string, unknown>;
        throw new FIClientError(
          response.status,
          (error?.detail as string) || response.statusText,
          error
        );
      }

      return response.json() as Promise<T>;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof FIClientError) {
        throw error;
      }
      if (error instanceof Error && error.name === 'AbortError') {
        throw new FIClientError(408, 'Request timeout', { timeout: this.config.timeout });
      }
      throw new FIClientError(0, 'Network error', { originalError: error });
    }
  }
}

/**
 * FI Client Error
 */
export class FIClientError extends Error {
  constructor(
    public status: number,
    message: string,
    public details?: unknown
  ) {
    super(message);
    this.name = 'FIClientError';
  }
}

/**
 * Default client factory
 */
export function createFIClient(config?: Partial<FIClientConfig>): FIClient {
  const defaultConfig: FIClientConfig = {
    baseUrl: process.env.FI_API_URL || 'http://localhost:7001',
    timeout: 30000,
    ...config,
  };
  return new FIClient(defaultConfig);
}
