export type LLMProvider = 'openai' | 'anthropic' | 'azure' | 'ollama';
export type CostTier = 'low' | 'medium' | 'high';

export interface LLMModel {
  id: string;
  label: string;
  provider: LLMProvider;
  cost_tier: CostTier;
  max_tokens: number;
  context_window: number;
  is_active: boolean;
  description?: string | null;
  size_bytes?: number | null;
  ram_required_gb?: number | null;
  created_at: string;
  updated_at: string;
}

export interface LLMModelCreate {
  id: string;
  label: string;
  provider: LLMProvider;
  cost_tier?: CostTier;
  max_tokens?: number;
  context_window?: number;
  is_active?: boolean;
  description?: string | null;
  size_bytes?: number | null;
  ram_required_gb?: number | null;
}

export type LLMModelUpdate = Partial<Omit<LLMModelCreate, 'id'>>;

export interface LLMModelFilter {
  includeInactive: boolean;
  provider?: LLMProvider;
}

export interface ModelTestResult {
  success: boolean;
  model_id: string;
  prompt: string;
  response: string;
  error?: string | null;
}

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

export interface CatalogQuery {
  source: CatalogSource;
  query?: string;
  maxSizeGb?: number;
  signal?: AbortSignal;
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

export interface InstallOptions {
  onProgress: (progress: InstallProgress) => void;
  signal?: AbortSignal;
}

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

// The I/O seam: a consumer wraps its own API client. A rejection's `Error.message` is shown as-is;
// `installCatalogModel` resolves when the download completes and rejects when it fails.
export interface ModelCatalogStore {
  listModels(filter: LLMModelFilter): Promise<LLMModel[]>;
  createModel(request: LLMModelCreate): Promise<LLMModel>;
  updateModel(modelId: string, request: LLMModelUpdate): Promise<LLMModel>;
  deactivateModel(modelId: string): Promise<void>;
  testModel(modelId: string): Promise<ModelTestResult>;
  listCatalog(query: CatalogQuery): Promise<CatalogModel[]>;
  installCatalogModel(modelId: string, options: InstallOptions): Promise<void>;
  removeCatalogModel(modelId: string): Promise<void>;
  getSystemResources(): Promise<SystemResources>;
  listRunningModels(): Promise<RunningModelsResponse>;
  unloadRunningModel(modelName: string): Promise<void>;
}

export type ModelCatalogConfirm = (message: string) => Promise<boolean>;

export type ModelCatalogNotify = (kind: 'success' | 'error', message: string) => void;

export const defaultModelCatalogConfirm: ModelCatalogConfirm = async (message) =>
  typeof window !== 'undefined' && typeof window.confirm === 'function' ? window.confirm(message) : false;

export const silentNotify: ModelCatalogNotify = () => {};

export function errorMessage(err: unknown, fallback: string): string {
  return err instanceof Error && err.message ? err.message : fallback;
}
