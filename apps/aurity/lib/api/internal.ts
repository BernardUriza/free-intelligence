/**
 * Internal API Client
 *
 * Client for backend internal endpoints (/internal/*).
 * Only accessible in development or from localhost.
 *
 * File: apps/aurity/lib/api/internal.ts
 * Created: 2025-11-08
 *
 * @warning These endpoints are NOT accessible in production from external clients.
 * Use workflows client for production.
 */

import { api } from './client';

function assertDevInternalAllowed(): void {
  const isProd = process.env.NODE_ENV === 'production';
  if (isProd) {
    throw new Error(
      'Internal API endpoints are not available in production. Use public orchestrator endpoints under /api/aurity or call the backend from server-side code.'
    );
  }
}

/**
 * Diarization endpoints (internal only)
 */
export const diarizationClient = {
  /**
   * Upload audio for diarization
   * POST /internal/diarization/upload
   */
  upload: async (audio: File, sessionId: string) => {
    // Guard: only allowed in non-production environments
    assertDevInternalAllowed();

    const formData = new FormData();
    formData.append('audio', audio);

    // Use centralized api.upload which attaches auth token
    return api.upload('/internal/diarization/upload', formData, {
      headers: {
        'X-Session-ID': sessionId,
      },
      retries: 2,
      timeout: 60_000,
    });
  },

  /**
   * Get job status
   * GET /internal/diarization/jobs/{jobId}
   */
  getJobStatus: (jobId: string) => {
    assertDevInternalAllowed();
    return api.get(`/internal/diarization/jobs/${jobId}`);
  },
};

/**
 * Transcription endpoints (internal only)
 */
export const transcribeClient = {
  /**
   * Transcribe audio
   * POST /internal/transcribe
   */
  transcribe: async (audio: File, sessionId: string) => {
    assertDevInternalAllowed();

    const formData = new FormData();
    formData.append('audio', audio);

    return api.upload('/internal/transcribe', formData, {
      headers: {
        'X-Session-ID': sessionId,
      },
      retries: 2,
      timeout: 60_000,
    });
  },
};

/**
 * Internal API client namespace
 *
 * @warning Only use in development or tests
 */
export const internalClient = {
  diarization: diarizationClient,
  transcribe: transcribeClient,
};
