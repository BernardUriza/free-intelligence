/**
 * System Resources API Client
 *
 * Cliente para monitorear recursos del sistema y modelos Ollama en ejecución.
 */

import { getBackendUrl } from '@/lib/config/deployment';

const BACKEND_URL = getBackendUrl();

// =============================================================================
// Types
// =============================================================================

export interface MemoryInfo {
  total_gb: number;
  available_gb: number;
  used_gb: number;
  percent_used: number;
}

export interface SystemResources {
  memory: MemoryInfo;
  cpu_percent: number;
  cpu_count: number;
  platform: string;
  timestamp: string;
}

export interface RunningModel {
  name: string;
  model_id: string;
  size_bytes: number;
  size_gb: number;
  vram_bytes: number | null;
  vram_gb: number | null;
  processor: 'cpu' | 'gpu' | 'partial';
  until: string | null;
}

export interface RunningModelsResponse {
  models: RunningModel[];
  total_loaded_gb: number;
  ollama_available: boolean;
}

export interface ModelCompatibility {
  model_id: string;
  ram_required_gb: number;
  ram_available_gb: number;
  can_run: boolean;
  warning: string | null;
}

// =============================================================================
// API Functions
// =============================================================================

const SYSTEM_BASE = '/api/admin/system';

/**
 * Obtiene recursos del sistema (RAM, CPU, plataforma).
 */
export async function fetchSystemResources(): Promise<SystemResources> {
  const response = await fetch(`${BACKEND_URL}${SYSTEM_BASE}/resources`);
  if (!response.ok) {
    throw new Error('Error al obtener recursos del sistema');
  }
  return response.json();
}

/**
 * Obtiene modelos Ollama actualmente cargados en memoria.
 */
export async function fetchRunningModels(): Promise<RunningModelsResponse> {
  const response = await fetch(`${BACKEND_URL}${SYSTEM_BASE}/ollama/running`);
  if (!response.ok) {
    throw new Error('Error al obtener modelos en ejecución');
  }
  return response.json();
}

/**
 * Verifica compatibilidad de un modelo con el sistema.
 */
export async function checkModelCompatibility(modelId: string): Promise<ModelCompatibility> {
  const response = await fetch(`${BACKEND_URL}${SYSTEM_BASE}/compatibility/${encodeURIComponent(modelId)}`);
  if (!response.ok) {
    throw new Error('Error al verificar compatibilidad');
  }
  return response.json();
}

/**
 * Descarga un modelo de la memoria de Ollama.
 */
export async function unloadModel(modelName: string): Promise<void> {
  const response = await fetch(`${BACKEND_URL}${SYSTEM_BASE}/ollama/unload/${encodeURIComponent(modelName)}`, {
    method: 'POST',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Error al descargar modelo');
  }
}

// =============================================================================
// Helpers
// =============================================================================

/**
 * Retorna color según porcentaje de uso.
 */
export function getUsageColor(percent: number): string {
  if (percent < 50) return 'emerald';
  if (percent < 75) return 'yellow';
  if (percent < 90) return 'orange';
  return 'red';
}

/**
 * Formatea el tiempo restante hasta descarga automática.
 */
export function formatTimeUntil(isoDate: string | null): string {
  if (!isoDate) return 'Persistente';

  const until = new Date(isoDate);
  const now = new Date();
  const diffMs = until.getTime() - now.getTime();

  if (diffMs <= 0) return 'Descargando...';

  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 60) return `${diffMin}m`;

  const diffHours = Math.floor(diffMin / 60);
  return `${diffHours}h ${diffMin % 60}m`;
}
