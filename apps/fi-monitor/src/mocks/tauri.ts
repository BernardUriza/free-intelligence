// Mock Tauri API for web development
export const mockInvoke = async (cmd: string, args?: any): Promise<any> => {
  console.log('[Mock Invoke]', cmd, args)

  switch (cmd) {
    case 'get_status':
      return {
        ollama_running: true,
        ollama_models: ['llama3.2', 'gemma2'],
        tunnel_running: false,
        tunnel_url: null,
        rag_service_running: true,
        gateway_running: true,
        system_info: {
          platform: 'darwin',
          hostname: 'MacBook-Pro'
        }
      }

    case 'list_ollama_models_detailed':
      return [
        {
          name: 'llama3.2:latest',
          size: '4.7 GB',
          modified: '2 days ago',
          digest: 'sha256:a1b2c3'
        },
        {
          name: 'gemma2:latest',
          size: '2.3 GB',
          modified: '1 week ago',
          digest: 'sha256:d4e5f6'
        },
        {
          name: 'qwen2.5:latest',
          size: '3.1 GB',
          modified: '3 days ago',
          digest: 'sha256:g7h8i9'
        }
      ]

    case 'pull_ollama_model':
      // Simulate pull with delay
      await new Promise(resolve => setTimeout(resolve, 2000))
      return null

    case 'delete_ollama_model':
      await new Promise(resolve => setTimeout(resolve, 500))
      return null

    case 'get_benchmark_history':
      const now = Date.now()
      const results = []

      // Generate 10 days of fake data
      for (let i = 0; i < 10; i++) {
        results.push({
          timestamp: new Date(now - i * 24 * 60 * 60 * 1000).toISOString(),
          rag_service: {
            single_query_ms: 30 + Math.random() * 20,
            batch_10_ms: 400 + Math.random() * 100,
            batch_32_ms: 900 + Math.random() * 200,
            batch_100_ms: 2500 + Math.random() * 500,
            throughput_qps: 250 + Math.random() * 50,
            gpu_memory_mb: 4096,
            device: 'mps',
            gpu_name: 'Apple M1 Max',
            model: 'all-MiniLM-L6-v2'
          },
          ollama: {
            single_query_ms: 800 + Math.random() * 200,
            batch_5_avg_ms: 850 + Math.random() * 150,
            tokens_per_sec: 60 + Math.random() * 20,
            model: 'llama3.2',
            eval_duration_ms: 800,
            eval_count: 50
          },
          gateway: {
            health_check_ms: 2 + Math.random() * 3,
            routing_overhead_ms: 1 + Math.random() * 2
          },
          total_duration_ms: 3000 + Math.random() * 500
        })
      }

      return { results }

    case 'start_ollama':
    case 'stop_ollama':
    case 'start_rag_service':
    case 'stop_rag_service':
    case 'start_gateway':
    case 'stop_gateway':
    case 'start_tunnel':
    case 'stop_tunnel':
      await new Promise(resolve => setTimeout(resolve, 1000))
      return true

    case 'test_ollama':
      await new Promise(resolve => setTimeout(resolve, 1500))
      return {
        category: 'math',
        question: '¿Cuánto es 2 + 2?',
        answer: '2 + 2 es igual a 4. Es una operación de suma básica.',
        elapsed_ms: 856,
        timestamp: new Date().toISOString()
      }

    case 'benchmark_all':
      await new Promise(resolve => setTimeout(resolve, 3000))
      return {
        timestamp: new Date().toISOString(),
        rag_service: {
          single_query_ms: 35,
          batch_10_ms: 450,
          batch_32_ms: 980,
          batch_100_ms: 2700,
          throughput_qps: 280,
          gpu_memory_mb: 4096,
          device: 'mps',
          gpu_name: 'Apple M1 Max',
          model: 'all-MiniLM-L6-v2'
        },
        ollama: {
          single_query_ms: 890,
          batch_5_avg_ms: 920,
          tokens_per_sec: 68,
          model: 'llama3.2',
          eval_duration_ms: 890,
          eval_count: 50
        },
        gateway: {
          health_check_ms: 3,
          routing_overhead_ms: 2
        },
        total_duration_ms: 3200
      }

    case 'get_tunnel_port':
      return 11400

    case 'set_tunnel_port':
      return null

    case 'read_tunnel_file':
      return JSON.stringify({
        tunnel_url: 'https://abc-123.trycloudflare.com',
        updated_at: new Date().toISOString()
      }, null, 2)

    case 'get_setup_state':
      return {
        completed: true,
        ollamaInstalled: true,
        pythonInstalled: true,
        lastCheck: new Date().toISOString(),
        skipped: false
      }

    case 'check_ollama_installed':
      return {
        installed: true,
        version: '0.5.0',
        install_path: '/usr/local/bin/ollama'
      }

    case 'check_python_installed':
      return {
        installed: true,
        version: '3.14.0',
        install_path: '/usr/local/bin/python3.14'
      }

    case 'mark_setup_completed':
    case 'mark_setup_skipped':
      return null

    case 'install_ollama_silent':
    case 'install_python_silent':
      await new Promise(resolve => setTimeout(resolve, 2000))
      return true

    case 'get_env_vars':
      return [
        { key: 'OLLAMA_NUM_PARALLEL', value: '1' },
        { key: 'OLLAMA_MAX_LOADED_MODELS', value: '1' },
        { key: 'OLLAMA_ORIGINS', value: '*' }
      ]

    case 'set_env_vars':
      await new Promise(resolve => setTimeout(resolve, 500))
      return null

    default:
      console.warn('[Mock Invoke] Unknown command:', cmd)
      return null
  }
}

export const mockListen = (event: string, handler: (e: any) => void) => {
  console.log('[Mock Listen]', event)

  // Simulate some events
  if (event === 'model-pull-completed') {
    setTimeout(() => {
      handler({ payload: 'llama3.3' })
    }, 3000)
  }

  return Promise.resolve(() => {
    console.log('[Mock Unlisten]', event)
  })
}

export const mockGetVersion = async () => '1.0.6'
