import type { CatalogModel, CatalogSource, CostTier, LLMModelCreate, LLMProvider, QuantizationType } from './types';

export const PROVIDER_INFO: Record<LLMProvider, { label: string }> = {
  openai: { label: 'OpenAI' },
  anthropic: { label: 'Anthropic' },
  azure: { label: 'Azure' },
  ollama: { label: 'Ollama (Local)' },
};

export const COST_TIER_INFO: Record<CostTier, { label: string; symbol: string }> = {
  low: { label: 'Económico', symbol: '$' },
  medium: { label: 'Balance', symbol: '$$' },
  high: { label: 'Premium', symbol: '$$$' },
};

export const SOURCE_INFO: Record<CatalogSource, { label: string }> = {
  gpt4all: { label: 'GPT4All' },
  huggingface: { label: 'HuggingFace' },
  ollama: { label: 'Ollama' },
};

export const QUANT_INFO: Record<QuantizationType, { label: string; quality: string }> = {
  Q4_0: { label: 'Q4_0', quality: 'Básica' },
  Q4_K_M: { label: 'Q4_K_M', quality: 'Balanceada' },
  Q5_K_M: { label: 'Q5_K_M', quality: 'Alta' },
  Q8_0: { label: 'Q8_0', quality: 'Muy Alta' },
  F16: { label: 'F16', quality: 'Máxima' },
  unknown: { label: 'Desconocida', quality: 'N/A' },
};

export const CATALOG_SOURCES: readonly CatalogSource[] = ['ollama', 'gpt4all', 'huggingface'];

export const FEATURED_MODEL_IDS: readonly string[] = [
  'llama-3.2-3b-instruct',
  'phi-3-mini',
  'mistral-7b-instruct',
  'qwen2.5-3b-instruct',
  'gemma-2-2b',
];

export const CATALOG_SIZE_OPTIONS: readonly { value: string; label: string }[] = [
  { value: '', label: 'Tamaño' },
  { value: '2', label: '≤ 2 GB' },
  { value: '4', label: '≤ 4 GB' },
  { value: '8', label: '≤ 8 GB' },
  { value: '16', label: '≤ 16 GB' },
];

export function isLocalProvider(provider: LLMProvider): boolean {
  return provider === 'ollama';
}

export function formatBytes(bytes: number): string {
  if (!bytes) return '0 B';
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.min(sizes.length - 1, Math.floor(Math.log(bytes) / Math.log(1000)));
  return `${(bytes / Math.pow(1000, i)).toFixed(1)} ${sizes[i]}`;
}

export function formatCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(0)}K`;
  return String(n);
}

export function formatDate(iso: string, locale: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleDateString(locale, { year: 'numeric', month: 'short', day: 'numeric' });
}

export function formatTimeUntil(iso: string | null, now: Date = new Date()): string {
  if (!iso) return 'Persistente';
  const diffMs = new Date(iso).getTime() - now.getTime();
  if (diffMs <= 0) return 'Descargando...';
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 60) return `${minutes}m`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

export function usageLevel(percent: number): 'ok' | 'warn' | 'danger' | 'critical' {
  if (percent < 50) return 'ok';
  if (percent < 75) return 'warn';
  if (percent < 90) return 'danger';
  return 'critical';
}

export function isFeaturedModel(model: CatalogModel): boolean {
  const id = model.id.toLowerCase();
  return FEATURED_MODEL_IDS.some((featured) => id.includes(featured));
}

/** The registry entry an installed catalog model becomes (always a local, low-cost Ollama model). */
export function catalogModelToCreate(model: CatalogModel): LLMModelCreate {
  return {
    id: model.id,
    label: model.name,
    provider: 'ollama',
    cost_tier: 'low',
    max_tokens: 4096,
    context_window: model.context_length || 4096,
    is_active: true,
    description: model.description || `${model.name} (${model.quantization})`,
    size_bytes: model.size_bytes,
    ram_required_gb: model.ram_required_gb || null,
  };
}

export function isAlreadyRegisteredError(err: unknown): boolean {
  const message = err instanceof Error ? err.message : '';
  return message.includes('already exists') || message.includes('duplicate');
}
