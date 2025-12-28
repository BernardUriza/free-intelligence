/**
 * Catalog API Client
 *
 * Cliente para el API del catálogo de modelos locales.
 * Soporta GPT4All, HuggingFace, y Ollama.
 */

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';

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

const CATALOG_BASE = '/api/admin/catalog';

/**
 * Lista modelos del catálogo con filtros opcionales.
 */
export async function fetchCatalogModels(
  params?: CatalogSearchParams
): Promise<CatalogListResponse> {
  const url = new URL(`${BACKEND_URL}${CATALOG_BASE}/models`);

  if (params?.source) url.searchParams.set('source', params.source);
  if (params?.query) url.searchParams.set('query', params.query);
  if (params?.max_size_gb) url.searchParams.set('max_size_gb', params.max_size_gb.toString());
  if (params?.max_ram_gb) url.searchParams.set('max_ram_gb', params.max_ram_gb.toString());
  if (params?.installed_only) url.searchParams.set('installed_only', 'true');
  if (params?.limit) url.searchParams.set('limit', params.limit.toString());
  if (params?.offset) url.searchParams.set('offset', params.offset.toString());

  const response = await fetch(url.toString(), {
    signal: params?.signal,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Error al cargar el catálogo');
  }
  return response.json();
}

/**
 * Obtiene el estado de disponibilidad de las fuentes.
 */
export async function fetchSourcesStatus(): Promise<SourcesStatus> {
  const response = await fetch(`${BACKEND_URL}${CATALOG_BASE}/sources/status`);
  if (!response.ok) {
    throw new Error('Error al verificar fuentes');
  }
  return response.json();
}

/**
 * Instala un modelo (síncrono, sin progreso).
 */
export async function installModel(modelId: string, source: CatalogSource): Promise<void> {
  const response = await fetch(`${BACKEND_URL}${CATALOG_BASE}/models/install`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_id: modelId, source }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Error al instalar el modelo');
  }
}

/**
 * Instala un modelo con streaming de progreso (SSE).
 * Includes 30-second inactivity timeout for robustness.
 */
export function installModelWithProgress(
  modelId: string,
  onProgress: (progress: InstallProgress) => void,
  onComplete: () => void,
  onError: (error: string) => void,
  timeoutMs: number = 30000
): () => void {
  const url = `${BACKEND_URL}${CATALOG_BASE}/models/${encodeURIComponent(modelId)}/install/stream`;

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
  const response = await fetch(
    `${BACKEND_URL}${CATALOG_BASE}/models/${encodeURIComponent(modelId)}`,
    { method: 'DELETE' }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Error al eliminar el modelo');
  }
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
 */
export const SOURCE_INFO: Record<CatalogSource, { label: string; color: string; icon: string }> = {
  gpt4all: { label: 'GPT4All', color: 'bg-emerald-500', icon: '🌿' },
  huggingface: { label: 'HuggingFace', color: 'bg-yellow-500', icon: '🤗' },
  ollama: { label: 'Ollama', color: 'bg-purple-500', icon: '🦙' },
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
