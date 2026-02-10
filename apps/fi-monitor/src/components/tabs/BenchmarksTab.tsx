import { BenchmarkCharts } from '../BenchmarkCharts'
import type { ServiceStatus, BenchmarkSuite } from '../../types/monitor'

interface BenchmarksTabProps {
  status: ServiceStatus | null
  benchmarkResults: BenchmarkSuite | null
  isBenchmarking: boolean
  runBenchmark: () => void
}

export function BenchmarksTab({
  status,
  benchmarkResults,
  isBenchmarking,
  runBenchmark,
}: BenchmarksTabProps) {
  return (
    <div className="p-4">
      <div className="benchmark-section">
      <div className="benchmark-header">
        <div className="benchmark-title">
          <span className="icon">{'\u26A1'}</span>
          <span>Performance Benchmark</span>
        </div>
        <button
          className="benchmark-btn"
          onClick={runBenchmark}
          disabled={isBenchmarking || !status?.rag_service_running}
        >
          {isBenchmarking ? '\u23F3 Running...' : '\u25B6 Run Suite'}
        </button>
      </div>

      {isBenchmarking && (
        <div className="benchmark-progress">
          Running benchmark suite... This may take 30-60 seconds.
        </div>
      )}

      {benchmarkResults && !isBenchmarking && (
        <>
          <table className="results-table">
            <thead>
              <tr>
                <th>Service</th>
                <th>Metric</th>
                <th>Value</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {benchmarkResults.rag_service && (
                <>
                  <tr>
                    <td rowSpan={6}>RAG Service</td>
                    <td>Single Query</td>
                    <td>{benchmarkResults.rag_service.single_query_ms}ms</td>
                    <td>{benchmarkResults.rag_service.single_query_ms < 50 ? '\u2705' : '\u26A0\uFE0F'}</td>
                  </tr>
                  <tr>
                    <td>Batch 10</td>
                    <td>{benchmarkResults.rag_service.batch_10_ms}ms</td>
                    <td>{benchmarkResults.rag_service.batch_10_ms < 500 ? '\u2705' : '\u26A0\uFE0F'}</td>
                  </tr>
                  <tr>
                    <td>Batch 32</td>
                    <td>{benchmarkResults.rag_service.batch_32_ms}ms</td>
                    <td>{benchmarkResults.rag_service.batch_32_ms < 1000 ? '\u2705' : '\u26A0\uFE0F'}</td>
                  </tr>
                  <tr>
                    <td>Batch 100</td>
                    <td>{benchmarkResults.rag_service.batch_100_ms}ms</td>
                    <td>-</td>
                  </tr>
                  <tr>
                    <td>Throughput</td>
                    <td>{benchmarkResults.rag_service.throughput_qps.toFixed(0)} qps</td>
                    <td>{benchmarkResults.rag_service.throughput_qps > 200 ? '\u2705' : '\u26A0\uFE0F'}</td>
                  </tr>
                  <tr>
                    <td>Device</td>
                    <td>{benchmarkResults.rag_service.device} ({benchmarkResults.rag_service.gpu_name || 'Unknown'})</td>
                    <td>{(benchmarkResults.rag_service.device === 'cuda' || benchmarkResults.rag_service.device === 'mps') ? '\u2705' : '\u274C'}</td>
                  </tr>
                </>
              )}
              {benchmarkResults.ollama && (
                <>
                  <tr>
                    <td rowSpan={2}>Ollama</td>
                    <td>Single Query</td>
                    <td>{benchmarkResults.ollama.single_query_ms}ms</td>
                    <td>-</td>
                  </tr>
                  <tr>
                    <td>Tokens/sec</td>
                    <td>{benchmarkResults.ollama.tokens_per_sec.toFixed(1)} t/s</td>
                    <td>{benchmarkResults.ollama.tokens_per_sec > 50 ? '\u2705' : '\u26A0\uFE0F'}</td>
                  </tr>
                </>
              )}
              {benchmarkResults.gateway && (
                <tr>
                  <td>Gateway</td>
                  <td>Health Check</td>
                  <td>{benchmarkResults.gateway.health_check_ms}ms</td>
                  <td>{benchmarkResults.gateway.health_check_ms < 10 ? '\u2705' : '\u26A0\uFE0F'}</td>
                </tr>
              )}
            </tbody>
          </table>

          <div className="benchmark-meta">
            <span>Total: {benchmarkResults.total_duration_ms}ms</span>
            <span>{'\u2022'}</span>
            <span>{new Date(benchmarkResults.timestamp).toLocaleString()}</span>
          </div>
        </>
      )}

      {!benchmarkResults && !isBenchmarking && (
        <div className="benchmark-placeholder">
          {status?.rag_service_running ? 'Click "Run Suite" to start benchmarking' : 'Start RAG Service first'}
        </div>
      )}
      </div>

      {/* Historical Performance Graphs */}
      <BenchmarkCharts />
    </div>
  )
}
