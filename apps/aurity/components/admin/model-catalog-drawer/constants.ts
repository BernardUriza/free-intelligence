/**
 * ModelCatalogDrawer Constants
 */

import { Library, CheckCircle } from 'lucide-react';
import type { CatalogSource } from '@/lib/api/catalog';
import type { FilterTab } from './types';

export const SOURCES: CatalogSource[] = ['ollama', 'gpt4all', 'huggingface'];

export const FEATURED_MODEL_IDS = [
  'llama-3.2-3b-instruct',
  'phi-3-mini',
  'mistral-7b-instruct',
  'qwen2.5-3b-instruct',
  'gemma-2-2b',
];

export const INITIAL_SOURCE_STATES = {
  ollama: { status: 'idle' as const, models: [] },
  gpt4all: { status: 'idle' as const, models: [] },
  huggingface: { status: 'idle' as const, models: [] },
};

export function getFilterTabs(installedCount: number): FilterTab[] {
  return [
    { key: 'all', label: 'Todos', icon: Library },
    { key: 'installed', label: 'Instalados', icon: CheckCircle, count: installedCount },
    { key: 'gpt4all', label: 'GPT4All', icon: 'provider' },
    { key: 'huggingface', label: 'HF', icon: 'provider' },
    { key: 'ollama', label: 'Ollama', icon: 'provider' },
  ];
}

export const SIZE_OPTIONS = [
  { value: '', label: 'Tamaño' },
  { value: '2', label: '≤ 2 GB' },
  { value: '4', label: '≤ 4 GB' },
  { value: '8', label: '≤ 8 GB' },
  { value: '16', label: '≤ 16 GB' },
];
