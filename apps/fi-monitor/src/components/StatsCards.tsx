interface StatsCardsProps {
  stats: {
    total_calls: number
    success_calls: number
    error_calls: number
    total_tokens: number
    avg_latency_ms: number
    min_latency_ms: number
    max_latency_ms: number
  }
}

export function StatsCards({ stats }: StatsCardsProps) {
  const successRate = stats.total_calls > 0
    ? ((stats.success_calls / stats.total_calls) * 100).toFixed(1)
    : '0'

  const formatNumber = (n: number) => {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
    return n.toString()
  }

  const getLatencyClass = (ms: number) => {
    if (ms < 500) return 'fast'
    if (ms < 2000) return 'medium'
    return 'slow'
  }

  return (
    <div className="grid grid-4">
      {/* Total Calls */}
      <div className="card">
        <div className="card-title">Total Calls</div>
        <div className="stat-value">{formatNumber(stats.total_calls)}</div>
        <div className="stat-label">
          <span style={{ color: '#22c55e' }}>{stats.success_calls} success</span>
          {stats.error_calls > 0 && (
            <span style={{ color: '#ef4444', marginLeft: '0.5rem' }}>
              {stats.error_calls} errors
            </span>
          )}
        </div>
      </div>

      {/* Success Rate */}
      <div className="card">
        <div className="card-title">Success Rate</div>
        <div className="stat-value" style={{ color: parseFloat(successRate) >= 99 ? '#22c55e' : '#f59e0b' }}>
          {successRate}%
        </div>
        <div className="stat-label">
          {stats.error_calls === 0 ? 'No errors' : `${stats.error_calls} failed`}
        </div>
      </div>

      {/* Total Tokens */}
      <div className="card">
        <div className="card-title">Total Tokens</div>
        <div className="stat-value">{formatNumber(stats.total_tokens)}</div>
        <div className="stat-label">
          ~{formatNumber(Math.round(stats.total_tokens / Math.max(stats.total_calls, 1)))} per call
        </div>
      </div>

      {/* Latency */}
      <div className="card">
        <div className="card-title">Avg Latency</div>
        <div className={`stat-value latency ${getLatencyClass(stats.avg_latency_ms)}`}>
          {Math.round(stats.avg_latency_ms)}ms
        </div>
        <div className="stat-label">
          Min: {stats.min_latency_ms}ms / Max: {stats.max_latency_ms}ms
        </div>
      </div>
    </div>
  )
}
