/**
 * Catalog API Client
 *
 * Cliente para el API del catálogo de modelos locales.
 * Soporta GPT4All, HuggingFace, y Ollama.
 *
 * Updated: 2026-02 - Migrated to centralized api client
 */

import { api, getBackendUrl } from './client';
import { ROUTES } from './routes';

// =============================================================================
// Types
// =============================================================================

export type CatalogSource = 'gpt4all' | 'huggingface' | 'ollama';

export type QuantizationType = 'Q4_0' | 'Q4_K_M' | 'Q5_K_M' | 'Q8_0' | 'F16' | 'unknown';

export interface CatalogModel {
  id: string;
  name: string;
  filename: string;
  source: CatalogSource;
  source_url?: string;
  repo_id?: string;
  size_bytes: number;
  ram_required_gb?: number;
  parameters?: string;
  quantization: QuantizationType;
  context_length?: number;
  description?: string;
  license?: string;
  tags: string[];
  is_installed: boolean;
  installed_at?: string;
}

export interface CatalogListResponse {
  models: CatalogModel[];
  total: number;
  sources_status: {
    gpt4all: boolean;
    huggingface: boolean;
    ollama: boolean;
  };
}

export interface SourcesStatus {
  gpt4all: boolean;
  huggingface: boolean;
  ollama: boolean;
}

export interface InstallProgress {
  model_id: string;
  status: 'downloading' | 'extracting' | 'registering' | 'completed' | 'error';
  progress_percent: number;
  downloaded_bytes: number;
  total_bytes: number;
  message?: string;
  error?: string;
}

export interface CatalogSearchParams {
  source?: CatalogSource;
  query?: string;
  max_size_gb?: number;
  max_ram_gb?: number;
  installed_only?: boolean;
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
}

// =============================================================================
// API Functions
// =============================================================================

const CATALOG_BASE = ROUTES.adminCatalog;

/**
 * Lista modelos del catálogo con filtros opcionales.
 */
export async function fetchCatalogModels(
  params?: CatalogSearchParams
): Promise<CatalogListResponse> {
  const queryParams = new URLSearchParams();

  if (params?.source) queryParams.set('source', params.source);
  if (params?.query) queryParams.set('query', params.query);
  if (params?.max_size_gb) queryParams.set('max_size_gb', params.max_size_gb.toString());
  if (params?.max_ram_gb) queryParams.set('max_ram_gb', params.max_ram_gb.toString());
  if (params?.installed_only) queryParams.set('installed_only', 'true');
  if (params?.limit) queryParams.set('limit', params.limit.toString());
  if (params?.offset) queryParams.set('offset', params.offset.toString());

  const queryString = queryParams.toString();
  const endpoint = queryString
    ? `${CATALOG_BASE}/models?${queryString}`
    : `${CATALOG_BASE}/models`;

  return api.get<CatalogListResponse>(endpoint, { signal: params?.signal });
}

/**
 * Obtiene el estado de disponibilidad de las fuentes.
 */
export async function fetchSourcesStatus(): Promise<SourcesStatus> {
  return api.get<SourcesStatus>(`${CATALOG_BASE}/sources/status`);
}

/**
 * Instala un modelo (síncrono, sin progreso).
 */
export async function installModel(modelId: string, source: CatalogSource): Promise<void> {
  await api.post(`${CATALOG_BASE}/models/install`, { model_id: modelId, source });
}

/**
 * Instala un modelo con streaming de progreso (SSE).
 * Includes 30-second inactivity timeout for robustness.
 *
 * Note: Uses direct EventSource for SSE streaming (api client doesn't support SSE)
 */
export function installModelWithProgress(
  modelId: string,
  onProgress: (progress: InstallProgress) => void,
  onComplete: () => void,
  onError: (error: string) => void,
  timeoutMs: number = 30000
): () => void {
  // EventSource requires full URL - SSE streaming not supported by api client
  const backendUrl = getBackendUrl();
  const url = `${backendUrl}${CATALOG_BASE}/models/${encodeURIComponent(modelId)}/install/stream`;

  const eventSource = new EventSource(url);
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  let lastActivity = Date.now();

  // Reset timeout on activity
  const resetTimeout = () => {
    lastActivity = Date.now();
    if (timeoutId) clearTimeout(timeoutId);
    timeoutId = setTimeout(() => {
      const elapsed = Date.now() - lastActivity;
      if (elapsed >= timeoutMs) {
        eventSource.close();
        onError(`Timeout: sin actividad por ${Math.round(timeoutMs / 1000)}s`);
      }
    }, timeoutMs);
  };

  // Start initial timeout
  resetTimeout();

  eventSource.onmessage = (event) => {
    resetTimeout();
    try {
      const progress: InstallProgress = JSON.parse(event.data);
      onProgress(progress);

      if (progress.status === 'completed') {
        if (timeoutId) clearTimeout(timeoutId);
        eventSource.close();
        onComplete();
      } else if (progress.status === 'error') {
        if (timeoutId) clearTimeout(timeoutId);
        eventSource.close();
        onError(progress.error || 'Error desconocido');
      }
    } catch (parseErr) {
      console.warn('[SSE] Parse error:', parseErr, 'Data:', event.data);
      // Continue listening - parse errors are recoverable
    }
  };

  eventSource.onerror = (err) => {
    if (timeoutId) clearTimeout(timeoutId);
    eventSource.close();
    console.error('[SSE] Connection error:', err);
    onError('Conexión perdida con el servidor');
  };

  // Return cleanup function
  return () => {
    if (timeoutId) clearTimeout(timeoutId);
    eventSource.close();
  };
}

/**
 * Elimina un modelo instalado de Ollama.
 */
export async function deleteInstalledModel(modelId: string): Promise<void> {
  await api.delete(`${CATALOG_BASE}/models/${encodeURIComponent(modelId)}`);
}

// =============================================================================
// Helpers
// =============================================================================

/**
 * Formatea bytes a tamaño legible.
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1000;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

/**
 * Información visual por fuente.
 * Note: Icons are now handled by ProviderLogo component using source key
 */
export const SOURCE_INFO: Record<CatalogSource, { label: string; color: string }> = {
  gpt4all: { label: 'GPT4All', color: 'bg-emerald-500' },
  huggingface: { label: 'HuggingFace', color: 'bg-yellow-500' },
  ollama: { label: 'Ollama', color: 'bg-purple-500' },
};

/**
 * Información visual por cuantización.
 */
export const QUANT_INFO: Record<QuantizationType, { label: string; quality: string }> = {
  Q4_0: { label: 'Q4_0', quality: 'Básica' },
  Q4_K_M: { label: 'Q4_K_M', quality: 'Balanceada' },
  Q5_K_M: { label: 'Q5_K_M', quality: 'Alta' },
  Q8_0: { label: 'Q8_0', quality: 'Muy Alta' },
  F16: { label: 'F16', quality: 'Máxima' },
  unknown: { label: 'Desconocida', quality: 'N/A' },
};
