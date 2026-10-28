/**
 * Catalog API Client — the local-model catalog (GPT4All, HuggingFace, Ollama).
 * Types come from fi-glass/model-catalog, which renders this data.
 */

import type { CatalogModel, CatalogSource, InstallOptions, InstallProgress } from 'fi-glass/model-catalog';
import { api, getBackendUrl } from './client';
import { ROUTES } from './routes';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('Catalog');

export interface CatalogListResponse {
  models: CatalogModel[];
  total: number;
  sources_status: Record<CatalogSource, boolean>;
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

/** Installs over SSE: resolves on `completed`; rejects on `error`, a lost stream, abort or `timeoutMs` idle. */
export function installModelWithProgress(
  modelId: string,
  { onProgress, signal }: InstallOptions,
  timeoutMs = 30000,
): Promise<void> {
  const url = `${getBackendUrl()}${CATALOG_BASE}/models/${encodeURIComponent(modelId)}/install/stream`;
  return new Promise<void>((resolve, reject) => {
    const eventSource = new EventSource(url);
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    const finish = (error?: Error) => {
      if (timeoutId) clearTimeout(timeoutId);
      eventSource.close();
      signal?.removeEventListener('abort', onAbort);
      if (error) reject(error);
      else resolve();
    };
    const onAbort = () => finish(new DOMException('Instalación cancelada', 'AbortError'));
    const armTimeout = () => {
      if (timeoutId) clearTimeout(timeoutId);
      timeoutId = setTimeout(
        () => finish(new Error(`Timeout: sin actividad por ${Math.round(timeoutMs / 1000)}s`)),
        timeoutMs,
      );
    };
    if (signal?.aborted) return onAbort();
    signal?.addEventListener('abort', onAbort);
    armTimeout();

    eventSource.onmessage = (event) => {
      armTimeout();
      let progress: InstallProgress;
      try {
        progress = JSON.parse(event.data);
      } catch (parseErr) {
        log.warn('SSE parse error', { error: String(parseErr) });
        return;
      }
      onProgress(progress);
      if (progress.status === 'completed') finish();
      else if (progress.status === 'error') finish(new Error(progress.error || 'Error desconocido'));
    };
    eventSource.onerror = (err) => {
      log.error('SSE connection error', { error: String(err) });
      finish(new Error('Conexión perdida con el servidor'));
    };
  });
}

/**
 * Elimina un modelo instalado de Ollama.
 */
export async function deleteInstalledModel(modelId: string): Promise<void> {
  await api.delete(`${CATALOG_BASE}/models/${encodeURIComponent(modelId)}`);
}
