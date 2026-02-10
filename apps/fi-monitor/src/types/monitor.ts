export interface ServiceStatus {
  ollama_running: boolean
  ollama_models: string[]
  tunnel_running: boolean
  tunnel_url: string | null
  rag_service_running: boolean
  gateway_running: boolean
  system_info: { platform: string; hostname: string }
}

export interface TestResult {
  category: string
  question: string
  answer: string
  elapsed_ms: number
  timestamp: string
  rag_metadata?: Record<string, unknown> | null
}

export interface SetupState {
  completed: boolean
  ollamaInstalled: boolean
  pythonInstalled: boolean
  lastCheck: string | null
  skipped: boolean
}

export interface RagBenchmark {
  single_query_ms: number
  batch_10_ms: number
  batch_32_ms: number
  batch_100_ms: number
  throughput_qps: number
  gpu_memory_mb: number
  device: string
  gpu_name: string | null
  model: string
}

export interface RagStats {
  gpu_memory_used_mb: number
  gpu_memory_total_mb: number
  gpu_device: string
  model_name: string
  embeddings_count: number
  avg_query_ms: number
  throughput_qps: number
}

export interface OllamaBenchmark {
  single_query_ms: number
  batch_5_avg_ms: number
  tokens_per_sec: number
  model: string
  eval_duration_ms: number
  eval_count: number
}

export interface GatewayBenchmark {
  health_check_ms: number
  routing_overhead_ms: number
}

export interface BenchmarkSuite {
  timestamp: string
  rag_service: RagBenchmark | null
  ollama: OllamaBenchmark | null
  gateway: GatewayBenchmark | null
  total_duration_ms: number
}

export interface BenchmarkHistory {
  results: BenchmarkSuite[]
}

export type TabId = 'services' | 'tunnel' | 'config' | 'testing' | 'benchmarks'

export interface Tab {
  id: TabId
  label: string
  icon: string
}
