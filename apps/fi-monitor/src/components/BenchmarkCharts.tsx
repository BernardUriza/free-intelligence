import { useState, useEffect, useCallback, useMemo } from 'react';
import { invoke } from '../lib/tauri-adapter';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';
import { BarChart3, Bot, Search, DoorOpen } from 'lucide-react';
import type { BenchmarkHistory, BenchmarkSuite } from '../types/monitor';

// ── Constants ────────────────────────────────────────────────────────

type TimeRange = '24h' | '7d' | '30d' | 'all';

const TIME_RANGE_OPTIONS: { value: TimeRange; label: string }[] = [
  { value: '24h', label: '24h' },
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' },
  { value: 'all', label: 'All' },
];

const CUTOFF_MS: Record<TimeRange, number> = {
  '24h': 24 * 60 * 60 * 1000,
  '7d': 7 * 24 * 60 * 60 * 1000,
  '30d': 30 * 24 * 60 * 60 * 1000,
  all: Infinity,
};

const AXIS_STYLE = { fontSize: '10px' } as const;
const AXIS_STROKE = '#888';
const GRID_STROKE = 'rgba(255,255,255,0.1)';

const TOOLTIP_STYLE = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: '4px',
  fontSize: '11px',
} as const;

const LEGEND_STYLE = { fontSize: '11px' } as const;
const DOT_CONFIG = { r: 3 };
const CHART_HEIGHT = 180;
const CHART_HEIGHT_SM = 150;

// ── Helpers ──────────────────────────────────────────────────────────

function formatDate(timestamp: string): string {
  return new Date(timestamp).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

function filterByTimeRange(
  results: BenchmarkSuite[],
  range: TimeRange,
): BenchmarkSuite[] {
  const now = Date.now();
  const cutoff = CUTOFF_MS[range];
  return results.filter(
    (r) => now - new Date(r.timestamp).getTime() < cutoff,
  );
}

// ── Shared Chart Primitives ──────────────────────────────────────────

function ChartGrid() {
  return <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />;
}

function ChartXAxis() {
  return <XAxis dataKey="date" stroke={AXIS_STROKE} style={AXIS_STYLE} />;
}

function ChartYAxis() {
  return <YAxis stroke={AXIS_STROKE} style={AXIS_STYLE} />;
}

function ChartTooltip() {
  return <Tooltip contentStyle={TOOLTIP_STYLE} />;
}

function ChartLegend() {
  return <Legend wrapperStyle={LEGEND_STYLE} />;
}

// ── Component ────────────────────────────────────────────────────────

export function BenchmarkCharts() {
  const [history, setHistory] = useState<BenchmarkHistory | null>(null);
  const [timeRange, setTimeRange] = useState<TimeRange>('7d');
  const [loading, setLoading] = useState(true);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    try {
      const result = await invoke<BenchmarkHistory>('get_benchmark_history');
      setHistory(result);
    } catch (error) {
      console.error('[BenchmarkCharts] Failed to load history:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const filtered = useMemo(
    () => filterByTimeRange(history?.results ?? [], timeRange),
    [history, timeRange],
  );

  const ollamaData = useMemo(
    () =>
      filtered
        .filter((r): r is BenchmarkSuite & { ollama: NonNullable<BenchmarkSuite['ollama']> } => r.ollama !== null)
        .map((r) => ({
          date: formatDate(r.timestamp),
          latency: r.ollama.single_query_ms,
          tokens_per_sec: r.ollama.tokens_per_sec,
        })),
    [filtered],
  );

  const ragData = useMemo(
    () =>
      filtered
        .filter((r): r is BenchmarkSuite & { rag_service: NonNullable<BenchmarkSuite['rag_service']> } => r.rag_service !== null)
        .map((r) => ({
          date: formatDate(r.timestamp),
          throughput: r.rag_service.throughput_qps,
          batch_10: r.rag_service.batch_10_ms,
          batch_32: r.rag_service.batch_32_ms,
        })),
    [filtered],
  );

  const gatewayData = useMemo(
    () =>
      filtered
        .filter((r): r is BenchmarkSuite & { gateway: NonNullable<BenchmarkSuite['gateway']> } => r.gateway !== null)
        .map((r) => ({
          date: formatDate(r.timestamp),
          health_check: r.gateway.health_check_ms,
        })),
    [filtered],
  );

  if (loading) {
    return (
      <div className="benchmark-charts loading">
        <div className="spinner" />
        <span>Loading historical data...</span>
      </div>
    );
  }

  if (!history || history.results.length === 0) {
    return (
      <div className="benchmark-charts empty">
        <p><BarChart3 size={16} style={{ verticalAlign: 'middle' }} /> No historical data yet.</p>
        <p>Run benchmarks to start tracking performance over time.</p>
      </div>
    );
  }

  return (
    <div className="benchmark-charts">
      {/* Time Range Selector */}
      <div className="chart-controls">
        <span className="chart-controls-label">Time Range:</span>
        {TIME_RANGE_OPTIONS.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setTimeRange(value)}
            className={timeRange === value ? 'active' : ''}
          >
            {label}
          </button>
        ))}
        <span className="chart-data-points">{filtered.length} data points</span>
      </div>

      {/* Ollama Performance Charts */}
      {ollamaData.length > 0 && (
        <div className="chart-section">
          <h4><Bot size={16} style={{ verticalAlign: 'middle' }} /> Ollama Performance</h4>
          <div className="chart-grid">
            <div className="chart-container">
              <h5>Query Latency (ms)</h5>
              <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                <LineChart data={ollamaData}>
                  <ChartGrid />
                  <ChartXAxis />
                  <ChartYAxis />
                  <ChartTooltip />
                  <ChartLegend />
                  <Line
                    type="monotone"
                    dataKey="latency"
                    stroke="#4caf50"
                    strokeWidth={2}
                    dot={DOT_CONFIG}
                    name="Latency (ms)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-container">
              <h5>Tokens/second</h5>
              <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                <LineChart data={ollamaData}>
                  <ChartGrid />
                  <ChartXAxis />
                  <ChartYAxis />
                  <ChartTooltip />
                  <ChartLegend />
                  <Line
                    type="monotone"
                    dataKey="tokens_per_sec"
                    stroke="#2196f3"
                    strokeWidth={2}
                    dot={DOT_CONFIG}
                    name="Tokens/s"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* RAG Service Performance Charts */}
      {ragData.length > 0 && (
        <div className="chart-section">
          <h4><Search size={16} style={{ verticalAlign: 'middle' }} /> RAG Service Performance</h4>
          <div className="chart-grid">
            <div className="chart-container">
              <h5>Throughput (queries/sec)</h5>
              <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                <LineChart data={ragData}>
                  <ChartGrid />
                  <ChartXAxis />
                  <ChartYAxis />
                  <ChartTooltip />
                  <ChartLegend />
                  <Line
                    type="monotone"
                    dataKey="throughput"
                    stroke="#00bcd4"
                    strokeWidth={2}
                    dot={DOT_CONFIG}
                    name="QPS"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-container">
              <h5>Batch Performance (ms)</h5>
              <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                <BarChart data={ragData}>
                  <ChartGrid />
                  <ChartXAxis />
                  <ChartYAxis />
                  <ChartTooltip />
                  <ChartLegend />
                  <Bar dataKey="batch_10" fill="#ff9800" name="Batch 10" />
                  <Bar dataKey="batch_32" fill="#ff5722" name="Batch 32" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Gateway Performance Chart */}
      {gatewayData.length > 0 && (
        <div className="chart-section">
          <h4><DoorOpen size={16} style={{ verticalAlign: 'middle' }} /> Gateway Performance</h4>
          <div className="chart-container full-width">
            <h5>Health Check Latency (ms)</h5>
            <ResponsiveContainer width="100%" height={CHART_HEIGHT_SM}>
              <LineChart data={gatewayData}>
                <ChartGrid />
                <ChartXAxis />
                <ChartYAxis />
                <ChartTooltip />
                <ChartLegend />
                <Line
                  type="monotone"
                  dataKey="health_check"
                  stroke="#9c27b0"
                  strokeWidth={2}
                  dot={DOT_CONFIG}
                  name="Health Check (ms)"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
