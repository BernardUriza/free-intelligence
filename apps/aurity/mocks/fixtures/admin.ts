export const catalogModels = [
  {
    id: 'qwen2.5-32b-instruct',
    name: 'Qwen2.5 32B Instruct',
    status: 'installed',
    size_gb: 18,
    updated_at: new Date().toISOString(),
  },
  {
    id: 'llama3.1-8b-instruct',
    name: 'Llama 3.1 8B',
    status: 'available',
    size_gb: 6,
    updated_at: new Date().toISOString(),
  },
];

export const catalogSourcesStatus = {
  huggingface: 'reachable',
  ollama: 'reachable',
};

export const systemResources = {
  cpu: { used: 32, total: 64 },
  gpu: { used: 40, total: 80 },
  memory: { used_gb: 24, total_gb: 64 },
  disk: { used_gb: 120, total_gb: 500 },
};

export const runningModels = [{ name: 'qwen2.5-32b-instruct', status: 'loaded' }];

export const compatibility = {
  compatible: true,
  reasons: [],
};
