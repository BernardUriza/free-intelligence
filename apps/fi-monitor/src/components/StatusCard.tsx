interface StatusCardProps {
  status: {
    ollama: { status: string; models: string[] }
    model: { name: string | null; size_gb: number; loaded: boolean }
    system: { platform: string; hostname: string; cpu_percent?: number; memory_percent?: number }
    ollama_url: string
  }
}

export function StatusCard({ status }: StatusCardProps) {
  const isOllamaRunning = status.ollama.status === 'running'
  const isModelLoaded = status.model.loaded

  return (
    <div className="grid grid-3">
      {/* Ollama Status */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Ollama</span>
          <span className={`status-badge ${isOllamaRunning ? 'success' : 'error'}`}>
            <span className={`status-dot ${isOllamaRunning ? 'running' : 'stopped'}`}></span>
            {isOllamaRunning ? 'Running' : 'Stopped'}
          </span>
        </div>
        <div>
          <p style={{ fontSize: '0.875rem', color: '#94a3b8' }}>
            {status.ollama_url}
          </p>
          {status.ollama.models.length > 0 && (
            <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
              Models: {status.ollama.models.join(', ')}
            </p>
          )}
        </div>
      </div>

      {/* Model Status */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Active Model</span>
          <span className={`status-badge ${isModelLoaded ? 'success' : 'error'}`}>
            <span className={`status-dot ${isModelLoaded ? 'running' : 'stopped'}`}></span>
            {isModelLoaded ? 'Loaded' : 'Not Loaded'}
          </span>
        </div>
        <div>
          {status.model.name ? (
            <>
              <p style={{ fontSize: '1.25rem', fontWeight: 600, color: '#f1f5f9' }}>
                {status.model.name}
              </p>
              <p style={{ fontSize: '0.75rem', color: '#64748b' }}>
                {status.model.size_gb} GB VRAM
              </p>
            </>
          ) : (
            <p style={{ fontSize: '0.875rem', color: '#64748b' }}>
              No model loaded
            </p>
          )}
        </div>
      </div>

      {/* System Status */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">System</span>
        </div>
        <div>
          <p style={{ fontSize: '1rem', fontWeight: 500, color: '#f1f5f9' }}>
            {status.system.hostname}
          </p>
          <p style={{ fontSize: '0.75rem', color: '#64748b' }}>
            {status.system.platform}
          </p>
          {status.system.cpu_percent !== undefined && (
            <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: '#94a3b8' }}>
              <span>CPU: {status.system.cpu_percent}%</span>
              {status.system.memory_percent !== undefined && (
                <span style={{ marginLeft: '1rem' }}>RAM: {status.system.memory_percent}%</span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
