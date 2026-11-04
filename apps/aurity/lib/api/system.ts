/**
 * System Resources API Client
 *
 * Cliente para monitorear recursos del sistema y modelos Ollama en ejecución.
 */

import type { RunningModelsResponse, SystemResources } from 'fi-glass/model-catalog';
import { api } from './client';
import { ROUTES } from './routes';

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
 * Descarga un modelo de la memoria de Ollama.
 */
export async function unloadModel(modelName: string): Promise<void> {
  await api.post<void>(`${API_BASE}/ollama/unload/${encodeURIComponent(modelName)}`);
}
