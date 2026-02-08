/**
 * System Resources API Client
 *
 * Cliente para monitorear recursos del sistema y modelos Ollama en ejecución.
 */

import { api } from './client';
import { ROUTES } from './routes';

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

const API_BASE = ROUTES.adminSystem;

/**
 * Obtiene recursos del sistema (RAM, CPU, plataforma).
 */
export async function fetchSystemResources(): Promise<SystemResources> {
  return api.get<SystemResources>(`${API_BASE}/resources`);
}

/**
 * Obtiene modelos Ollama actualmente cargados en memoria.
 */
export async function fetchRunningModels(): Promise<RunningModelsResponse> {
  return api.get<RunningModelsResponse>(`${API_BASE}/ollama/running`);
}

/**
 * Verifica compatibilidad de un modelo con el sistema.
 */
export async function checkModelCompatibility(modelId: string): Promise<ModelCompatibility> {
  return api.get<ModelCompatibility>(`${API_BASE}/compatibility/${encodeURIComponent(modelId)}`);
}

/**
 * Descarga un modelo de la memoria de Ollama.
 */
export async function unloadModel(modelName: string): Promise<void> {
  await api.post<void>(`${API_BASE}/ollama/unload/${encodeURIComponent(modelName)}`);
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
