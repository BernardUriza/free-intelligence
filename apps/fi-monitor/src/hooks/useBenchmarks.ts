import { useState, useEffect, useCallback } from 'react'
import { invoke, listen, isTauriContext } from '../lib/tauri-adapter'
import type { BenchmarkSuite, BenchmarkHistory } from '../types/monitor'

export function useBenchmarks(setError: (v: string | null) => void) {
  const [benchmarkResults, setBenchmarkResults] = useState<BenchmarkSuite | null>(null)
  const [isBenchmarking, setIsBenchmarking] = useState(false)

  const runBenchmark = useCallback(async () => {
    if (!isTauriContext()) {
      setError('Benchmark not available in browser mode')
      return
    }

    setIsBenchmarking(true)
    setError(null)
    try {
      const result = await invoke<BenchmarkSuite>('benchmark_all')
      setBenchmarkResults(result)
      const history = await invoke<BenchmarkHistory>('get_benchmark_history')
      console.log('[FI Monitor] Benchmark history loaded:', history.results.length, 'results')
    } catch (err) {
      setError(String(err))
    } finally {
      setIsBenchmarking(false)
    }
  }, [setError])

  // Benchmark event listener
  useEffect(() => {
    if (!isTauriContext()) {
      console.warn('[App] Skipping benchmark listener (not in Tauri context)')
      return
    }

    const unlistenBenchmark = listen<BenchmarkSuite>('benchmark-complete', (event) => {
      setBenchmarkResults(event.payload)
    })
    return () => {
      unlistenBenchmark.then(fn => fn())
    }
  }, [])

  return {
    benchmarkResults,
    isBenchmarking,
    runBenchmark,
  }
}
