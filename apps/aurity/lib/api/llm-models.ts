/**
 * LLM Models API Client
 *
 * Functions for managing LLM model configurations.
 * Superadmin only - CRUD operations.
 */

import type { LLMModel, LLMModelCreate, LLMModelUpdate, LLMProvider, ModelTestResult } from 'fi-glass/model-catalog';
import { api } from './client';
import { ROUTES } from './routes';

const API_BASE = ROUTES.adminLlmModels;

/**
 * Fetch all LLM models
 */
export async function fetchLLMModels(options?: {
  includeInactive?: boolean;
  provider?: LLMProvider;
}): Promise<LLMModel[]> {
  const params = new URLSearchParams();
  if (options?.includeInactive) {
    params.append('include_inactive', 'true');
  }
  if (options?.provider) {
    params.append('provider', options.provider);
  }

  const query = params.toString() ? `?${params}` : '';
  return api.get<LLMModel[]>(`${API_BASE}${query}`);
}

/**
 * Create a new LLM model
 */
export async function createLLMModel(data: LLMModelCreate): Promise<LLMModel> {
  return api.post<LLMModel>(API_BASE, data);
}

/**
 * Update an existing LLM model
 */
export async function updateLLMModel(modelId: string, data: LLMModelUpdate): Promise<LLMModel> {
  return api.put<LLMModel>(`${API_BASE}/${modelId}`, data);
}

/**
 * Delete (deactivate) an LLM model
 */
export async function deleteLLMModel(modelId: string, hardDelete = false): Promise<void> {
  const params = hardDelete ? '?hard_delete=true' : '';
  await api.delete<void>(`${API_BASE}/${modelId}${params}`);
}

/**
 * Test an LLM model with a random medical prompt
 */
export async function testLLMModel(modelId: string): Promise<ModelTestResult> {
  return api.post<ModelTestResult>(`${API_BASE}/${modelId}/test`);
}
