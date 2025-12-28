/**
 * Workflows API Client
 *
 * Client for backend orchestrator endpoints (/api/workflows/aurity/*).
 * Provides end-to-end consultation workflows.
 *
 * File: apps/aurity/lib/api/workflows.ts
 * Created: 2025-11-08
 */

import { api } from './client';

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
 * POST /api/workflows/aurity/consult
 */
export async function startConsultWorkflow(
  audio: File,
  sessionId: string
): Promise<ConsultStartResponse> {
  const formData = new FormData();
  formData.append('audio', audio);

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001'}/api/workflows/aurity/consult`,
    {
      method: 'POST',
      headers: {
        'X-Session-ID': sessionId,
      },
      body: formData,
    }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to start consultation: ${error}`);
  }

  return response.json();
}

/**
 * Get consultation workflow status
 * GET /api/workflows/aurity/consult/{jobId}
 */
export async function getConsultStatus(jobId: string): Promise<ConsultStatusResponse> {
  return api.get<ConsultStatusResponse>(`/api/workflows/aurity/consult/${jobId}`);
}

/**
 * Workflows client namespace
 */
export const workflowsClient = {
  startConsult: startConsultWorkflow,
  getStatus: getConsultStatus,
};
