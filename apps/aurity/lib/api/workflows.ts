/**
 * Workflows API Client
 *
 * Client for backend orchestrator endpoints (/api/aurity/*).
 * Provides end-to-end consultation workflows.
 *
 * File: apps/aurity/lib/api/workflows.ts
 * Created: 2025-11-08
 * Updated: 2026-02 - Migrated to centralized api client
 */

import { api } from './client';
import { ROUTES } from './routes';

export interface ConsultStartRequest {
  audio: File;
  sessionId: string;
}

export interface ConsultStartResponse {
  job_id: string;
  session_id: string;
  status: string;
  message: string;
}

export interface ConsultStatusResponse {
  job_id: string;
  session_id: string;
  status: string;
  progress_pct: number;
  stages: {
    upload: string;
    transcribe: string;
    diarize: string;
    soap: string;
  };
  soap_note?: {
    subjetivo: unknown;
    objetivo: unknown;
    analisis: unknown;
    plan: unknown;
    completeness: number;
  };
  error?: string;
}

/**
 * Start end-to-end consultation workflow
 * POST ROUTES.consult
 */
export async function startConsultWorkflow(
  audio: File,
  sessionId: string
): Promise<ConsultStartResponse> {
  const formData = new FormData();
  formData.append('audio', audio);

  // Use api.upload but we need custom headers, so we'll use a slightly different approach
  // The api.upload doesn't support custom headers, so we create formData and add session ID
  formData.append('session_id', sessionId);

  return api.upload<ConsultStartResponse>(ROUTES.consult, formData);
}

/**
 * Get consultation workflow status
 * GET ROUTES.consult/{jobId}
 */
export async function getConsultStatus(jobId: string): Promise<ConsultStatusResponse> {
  return api.get<ConsultStatusResponse>(`${ROUTES.consult}/${jobId}`);
}

/**
 * Workflows client namespace
 */
export const workflowsClient = {
  startConsult: startConsultWorkflow,
  getStatus: getConsultStatus,
};
