import { ModelManager } from '../ModelManager'
import { SERVICE_PORTS } from '../../lib/constants'
import type { ServiceStatus, RagStats } from '../../types/monitor'

interface ServicesTabProps {
  status: ServiceStatus | null
  ragStats: RagStats | null
  actionLoading: string | null
  handleAction: (action: string, command: string) => void
  showModelManager: boolean
  setShowModelManager: (v: boolean) => void
}

export function ServicesTab({
  status,
  ragStats,
  actionLoading,
  handleAction,
  showModelManager,
  setShowModelManager,
}: ServicesTabProps) {
  const ollamaOn = status?.ollama_running ?? false
  const ragOn = status?.rag_service_running ?? false
  const gatewayOn = status?.gateway_running ?? false

  const services = [
    {
      name: 'Ollama',
      port: SERVICE_PORTS.OLLAMA,
      icon: '\u{1F999}',
      running: ollamaOn,
      description: 'LLM Engine'
    },
    {
      name: 'RAG',
      port: SERVICE_PORTS.RAG,
      icon: '\u{1F50D}',
      running: ragOn,
      description: 'Embeddings'
    },
    {
      name: 'Gateway',
      port: SERVICE_PORTS.GATEWAY,
      icon: '\u{1F6AA}',
      running: gatewayOn,
      description: 'Router'
    }
  ]

  return (
    <div className="flex flex-col gap-4 p-4">
      {/* Services Topology (READ-ONLY) */}
      <div className="bg-app-surface rounded-lg border border-app-border p-2">
        <div className="flex items-center gap-1 mb-1">
          <span className="text-xs">{'\u{1F5FA}\uFE0F'}</span>
          <span className="text-xs font-medium text-app-text">Services Topology</span>
        </div>

        <div className="services-topology">
          {services.map(service => (
            <div
              key={service.port}
              className={`service-mini ${service.running ? 'active' : 'inactive'}`}
            >
              <div className="service-mini-icon">{service.icon}</div>
              <div className="service-mini-body">
                <div className="service-mini-name">{service.name}</div>
                <div className="service-mini-port">:{service.port}</div>
                <div className="service-mini-desc">{service.description}</div>
              </div>
              <div className={`service-mini-status ${service.running ? 'on' : 'off'}`}>
                {service.running ? '\u{1F7E2}' : '\u26AA'}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Service Control Cards */}
      <div className="services-grid">
        {/* Ollama */}
        <div className={`service-card ${ollamaOn ? 'active' : ''}`} style={{ flexDirection: 'column', alignItems: 'stretch' }}>
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
            <div className="service-icon">{'\u{1F999}'}</div>
            <div style={{ flex: 1 }}>
              <div className="service-name">Ollama</div>
              <div className={`service-status ${ollamaOn ? 'on' : 'off'}`}>
                {ollamaOn ? '\u25CF Activo' : '\u25CB Inactivo'}
              </div>
            </div>
            <button
              className={`action-btn ${ollamaOn ? 'stop' : 'start'}`}
              onClick={() => handleAction(ollamaOn ? 'ollama-stop' : 'ollama-start', ollamaOn ? 'stop_ollama' : 'start_ollama')}
              disabled={!!actionLoading}
            >
              {actionLoading?.includes('ollama') ? '...' : ollamaOn ? '\u25A0' : '\u25B6'}
            </button>
          </div>

          {/* Body */}
          <div>
            {ollamaOn && status?.ollama_models && status.ollama_models.length > 0 && (
              <div className="models" style={{ marginBottom: '8px' }}>{status.ollama_models.slice(0, 2).join(', ')}</div>
            )}
            {ollamaOn && (
              <button
                className="models-btn"
                onClick={() => setShowModelManager(!showModelManager)}
                style={{
                  marginBottom: '8px',
                  padding: '4px 8px',
                  fontSize: '11px',
                  background: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: '3px',
                  cursor: 'pointer',
                  color: 'var(--text-dim)'
                }}
              >
                {'\u{1F4E6}'} {showModelManager ? 'Hide' : 'Show'} Models
              </button>
            )}

          </div>
        </div>

        {/* RAG Service */}
        <div className={`service-card ${ragOn ? 'active' : ''} ${!ollamaOn ? 'disabled' : ''}`} style={{ flexDirection: 'column', alignItems: 'stretch' }}>
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
            <div className="service-icon">{'\u{1F50D}'}</div>
            <div style={{ flex: 1 }}>
              <div className="service-name">RAG Service</div>
              <div className={`service-status ${ragOn ? 'on' : 'off'}`}>
                {ragOn ? '\u25CF Activo' : '\u25CB Inactivo'}
              </div>
            </div>
          </div>

          {/* Stats (cuando esta activo) */}
          {ragOn && ragStats && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '11px', color: 'var(--text-dim)' }}>
              <div>
                <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: '2px' }}>GPU Memory</div>
                <div>{ragStats.gpu_memory_used_mb} MB / {(ragStats.gpu_memory_total_mb / 1024).toFixed(0)} GB</div>
                <div style={{ marginTop: '2px', fontSize: '10px' }}>{ragStats.gpu_device.toUpperCase()}</div>
              </div>
              <div>
                <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: '2px' }}>Model</div>
                <div>{ragStats.model_name}</div>
              </div>
              <div>
                <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: '2px' }}>Embeddings</div>
                <div>{ragStats.embeddings_count.toLocaleString()} chunks</div>
              </div>
              <div>
                <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: '2px' }}>Performance</div>
                <div>{ragStats.avg_query_ms.toFixed(1)}ms avg</div>
                <div>{ragStats.throughput_qps.toFixed(0)} QPS</div>
              </div>
            </div>
          )}

          {/* Loading state */}
          {ragOn && !ragStats && (
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', textAlign: 'center', padding: '12px' }}>
              Loading stats...
            </div>
          )}

          {/* Inactive state */}
          {!ragOn && (
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', textAlign: 'center', padding: '12px' }}>
              Auto-starts with Ollama
            </div>
          )}
        </div>
      </div>

      {/* Model Manager (conditional) */}
      {showModelManager && ollamaOn && <ModelManager />}
    </div>
  )
}
