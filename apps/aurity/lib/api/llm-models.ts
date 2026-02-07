/**
 * LLM Models API Client
 *
 * Functions for managing LLM model configurations.
 * Superadmin only - CRUD operations.
 */

import type { LLMModel, LLMModelCreate, LLMModelUpdate, LLMProvider } from '@aurity-standalone/types/llm';
import { api } from './client';

const API_BASE = '/api/admin/llm-models';

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
 * Fetch a specific LLM model by ID
 */
export async function fetchLLMModel(modelId: string): Promise<LLMModel> {
  return api.get<LLMModel>(`${API_BASE}/${modelId}`);
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
 * Get list of available providers
 */
export async function fetchProviders(): Promise<string[]> {
  return api.get<string[]>(`${API_BASE}/providers/list`);
}

/**
 * Get list of available cost tiers
 */
export async function fetchCostTiers(): Promise<string[]> {
  return api.get<string[]>(`${API_BASE}/cost-tiers/list`);
}

/**
 * Test response from model validation
 */
export interface ModelTestResult {
  success: boolean;
  model_id: string;
  prompt: string;
  response: string;
  error?: string | null;
}

/**
 * Test an LLM model with a random medical prompt
 */
export async function testLLMModel(modelId: string): Promise<ModelTestResult> {
  return api.post<ModelTestResult>(`${API_BASE}/${modelId}/test`);
}
