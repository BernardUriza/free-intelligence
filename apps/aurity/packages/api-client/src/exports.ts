/**
 * Free Intelligence - Export API Client
 *
 * Client for session export with manifest and hash verification.
 *
 * File: apps/aurity/lib/api/exports.ts
 * Cards: FI-UI-FEAT-203
 * Created: 2025-10-30
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:7001';

// ============================================================================
// TYPES
// ============================================================================

export interface ExportInclude {
  transcript: boolean;
  events: boolean;
  attachments: boolean;
}

export interface ExportRequest {
  sessionId: string;
  formats: ('md' | 'json')[];
  include: ExportInclude;
}

export interface ExportArtifact {
  format: 'md' | 'json' | 'manifest';
  url: string;
  sha256: string;
  bytes: number;
}

export interface ExportResponse {
  exportId: string;
  status: 'ready' | 'processing';
  artifacts: ExportArtifact[];
  manifestUrl: string;
}

export interface VerifyRequest {
  targets: ('md' | 'json' | 'manifest')[];
}

export interface VerifyResult {
  target: string;
  ok: boolean;
  message?: string | null;
}

export interface VerifyResponse {
  ok: boolean;
  results: VerifyResult[];
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

/**
 * Create export for session
 */
export async function createExport(
  request: ExportRequest
): Promise<ExportResponse> {
  const response = await fetch(`${API_BASE_URL}/api/exports`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to create export: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get export status
 */
export async function getExport(exportId: string): Promise<ExportResponse> {
  const response = await fetch(`${API_BASE_URL}/api/exports/${exportId}`);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Export ${exportId} not found`);
    }
    throw new Error(`Failed to get export: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Verify export integrity
 */
export async function verifyExport(
  exportId: string,
  request: VerifyRequest = { targets: ['md', 'json', 'manifest'] }
): Promise<VerifyResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/exports/${exportId}/verify`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to verify export: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Poll export until ready (with timeout)
 */
export async function pollExport(
  exportId: string,
  maxAttempts: number = 10,
  baseInterval: number = 1000
): Promise<ExportResponse> {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const exportData = await getExport(exportId);

    if (exportData.status === 'ready') {
      return exportData;
    }

    // Exponential backoff with jitter (800-1200ms)
    const jitter = Math.random() * 400 - 200; // -200 to +200
    const delay = baseInterval + jitter;
    await new Promise((resolve) => setTimeout(resolve, delay));
  }

  throw new Error('Export timeout: took too long to process');
}
