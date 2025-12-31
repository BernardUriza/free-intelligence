interface ModelData {
  model: string
  count: number
  tokens: number
  avg_latency_ms: number
}

interface ModelChartProps {
  data: ModelData[]
}

export function ModelChart({ data }: ModelChartProps) {
  const maxCount = Math.max(...data.map(d => d.count), 1)
  const total = data.reduce((sum, d) => sum + d.count, 0)

  const colors = [
    '#3b82f6', // blue
    '#8b5cf6', // purple
    '#06b6d4', // cyan
    '#10b981', // green
    '#f59e0b', // amber
  ]

  return (
    <div className="card">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {data.map((item, index) => {
          const percentage = ((item.count / total) * 100).toFixed(1)
          const barWidth = (item.count / maxCount) * 100
          const color = colors[index % colors.length]

          return (
            <div key={item.model}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                <span style={{ fontWeight: 500 }}>
                  <code style={{ background: '#334155', padding: '0.125rem 0.375rem', borderRadius: '0.25rem', fontSize: '0.875rem' }}>
                    {item.model}
                  </code>
                </span>
                <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
                  {item.count} calls ({percentage}%)
                </span>
              </div>
              <div style={{
                height: '1.5rem',
                background: '#334155',
                borderRadius: '0.25rem',
                overflow: 'hidden',
                position: 'relative'
              }}>
                <div style={{
                  width: `${barWidth}%`,
                  height: '100%',
                  background: color,
                  borderRadius: '0.25rem',
                  transition: 'width 0.3s ease',
                  display: 'flex',
                  alignItems: 'center',
                  paddingLeft: '0.5rem',
                }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 500, color: 'white' }}>
                    {item.tokens.toLocaleString()} tokens
                  </span>
                </div>
              </div>
              <div style={{
                display: 'flex',
                gap: '1rem',
                marginTop: '0.25rem',
                fontSize: '0.75rem',
                color: '#64748b'
              }}>
                <span>Avg latency: {Math.round(item.avg_latency_ms)}ms</span>
                <span>~{Math.round(item.tokens / Math.max(item.count, 1))} tokens/call</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
