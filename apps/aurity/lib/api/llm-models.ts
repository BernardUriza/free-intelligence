/**
 * LLM Models API Client
 *
 * Functions for managing LLM model configurations.
 * Superadmin only - CRUD operations.
 */

import type { LLMModel, LLMModelCreate, LLMModelUpdate, LLMProvider } from '@aurity-standalone/types/llm';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';

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

  const url = `${BACKEND_URL}/api/admin/llm-models${params.toString() ? `?${params}` : ''}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch LLM models: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch a specific LLM model by ID
 */
export async function fetchLLMModel(modelId: string): Promise<LLMModel> {
  const response = await fetch(`${BACKEND_URL}/api/admin/llm-models/${modelId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch LLM model ${modelId}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Create a new LLM model
 */
export async function createLLMModel(data: LLMModelCreate): Promise<LLMModel> {
  const response = await fetch(`${BACKEND_URL}/api/admin/llm-models`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to create LLM model: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Update an existing LLM model
 */
export async function updateLLMModel(modelId: string, data: LLMModelUpdate): Promise<LLMModel> {
  const response = await fetch(`${BACKEND_URL}/api/admin/llm-models/${modelId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to update LLM model ${modelId}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete (deactivate) an LLM model
 */
export async function deleteLLMModel(modelId: string, hardDelete = false): Promise<void> {
  const params = hardDelete ? '?hard_delete=true' : '';
  const response = await fetch(`${BACKEND_URL}/api/admin/llm-models/${modelId}${params}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to delete LLM model ${modelId}: ${response.statusText}`);
  }
}

/**
 * Get list of available providers
 */
export async function fetchProviders(): Promise<string[]> {
  const response = await fetch(`${BACKEND_URL}/api/admin/llm-models/providers/list`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch providers: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get list of available cost tiers
 */
export async function fetchCostTiers(): Promise<string[]> {
  const response = await fetch(`${BACKEND_URL}/api/admin/llm-models/cost-tiers/list`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch cost tiers: ${response.statusText}`);
  }

  return response.json();
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
  const response = await fetch(`${BACKEND_URL}/api/admin/llm-models/${modelId}/test`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to test model ${modelId}: ${response.statusText}`);
  }

  return response.json();
}
