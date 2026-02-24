import { useState, useEffect, useCallback } from 'react';
import { invoke, listen, isTauriContext } from '../lib/tauri-adapter';
import type { BenchmarkSuite, BenchmarkHistory } from '../types/monitor';

// ── Constants ────────────────────────────────────────────────────────

const BENCHMARK_COMPLETE_EVENT = 'benchmark-complete';
const LOG_PREFIX = '[useBenchmarks]';

// ── Hook ─────────────────────────────────────────────────────────────

export function useBenchmarks(setError: (v: string | null) => void) {
  const [benchmarkResults, setBenchmarkResults] = useState<BenchmarkSuite | null>(null);
  const [isBenchmarking, setIsBenchmarking] = useState(false);

  const runBenchmark = useCallback(async () => {
    if (!isTauriContext()) {
      setError('Benchmark not available in browser mode');
      return;
    }

    setIsBenchmarking(true);
    setError(null);
    try {
      const result = await invoke<BenchmarkSuite>('benchmark_all');
      setBenchmarkResults(result);

      const history = await invoke<BenchmarkHistory>('get_benchmark_history');
      console.log(`${LOG_PREFIX} History loaded:`, history.results.length, 'results');
    } catch (err) {
      setError(String(err));
    } finally {
      setIsBenchmarking(false);
    }
  }, [setError]);

  useEffect(() => {
    if (!isTauriContext()) {
      console.warn(`${LOG_PREFIX} Skipping listener (not in Tauri context)`);
      return;
    }

    const unlisten = listen<BenchmarkSuite>(BENCHMARK_COMPLETE_EVENT, (event) => {
      setBenchmarkResults(event.payload);
    });

    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  return {
    benchmarkResults,
    isBenchmarking,
    runBenchmark,
  } as const;
}
