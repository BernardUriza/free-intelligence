import { EnvVarEditor } from '../EnvVarEditor'
import { SERVICE_PORTS } from '../../lib/constants'
import type { ServiceStatus } from '../../types/monitor'

interface ConfigTabProps {
  status: ServiceStatus | null
  tunnelPort: string
  setTunnelPort: (v: string) => void
  tunnelPortError: string | null
  setTunnelPortError: (v: string | null) => void
  savedTunnelPort: string
  tunnelOn: boolean
  handleSaveTunnelPort: () => void
}

export function ConfigTab({
  status,
  tunnelPort,
  setTunnelPort,
  tunnelPortError,
  setTunnelPortError,
  savedTunnelPort,
  tunnelOn,
  handleSaveTunnelPort,
}: ConfigTabProps) {
  const portChanged = tunnelPort !== savedTunnelPort
  const portValid = !isNaN(parseInt(tunnelPort, 10)) &&
                    parseInt(tunnelPort, 10) >= 1024 &&
                    parseInt(tunnelPort, 10) <= 65535

  const isPortOccupied = (port: number): boolean => {
    if (port === SERVICE_PORTS.OLLAMA) return status?.ollama_running || false
    if (port === SERVICE_PORTS.RAG) return status?.rag_service_running || false
    if (port === SERVICE_PORTS.GATEWAY) return status?.gateway_running || false
    return false
  }

  const handlePortSelect = (port: number) => {
    if (tunnelOn) {
      setTunnelPortError('Stop tunnel first to change port')
      return
    }
    if (isPortOccupied(port)) {
      setTunnelPortError(`Port ${port} is in use by another service`)
      return
    }
    setTunnelPort(String(port))
    setTunnelPortError(null)
  }

  const portOptions = [
    {
      port: SERVICE_PORTS.GATEWAY,
      label: 'Gateway',
      description: 'Enruta /api \u2192 Ollama, /rag \u2192 RAG',
      recommended: true,
      occupied: isPortOccupied(SERVICE_PORTS.GATEWAY)
    },
    {
      port: SERVICE_PORTS.OLLAMA,
      label: 'Ollama Direct',
      description: 'Bypass Gateway - Direct LLM access',
      recommended: false,
      occupied: isPortOccupied(SERVICE_PORTS.OLLAMA)
    },
    {
      port: SERVICE_PORTS.RAG,
      label: 'RAG Direct',
      description: 'Bypass Gateway - Direct embeddings access',
      recommended: false,
      occupied: isPortOccupied(SERVICE_PORTS.RAG)
    }
  ]

  return (
    <>
    <div className="grid grid-cols-2 gap-3 p-3">
      {/* ===== Port Configuration (RADIO CARDS) - Left Column ===== */}
      <div className="bg-app-surface rounded-lg border border-app-border p-3 flex flex-col">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-sm">{'\u{1F50C}'}</span>
            <span className="text-xs font-medium text-app-text">Tunnel Port Configuration</span>
          </div>
          {portChanged && (
            <span className="text-xs text-app-warning">{'\u25CF'} Unsaved</span>
          )}
        </div>

        {/* Radio button cards for presets */}
        <div className="port-options-grid">
          {portOptions.map(option => {
            const isSelected = parseInt(tunnelPort) === option.port
            const isDisabled = tunnelOn || option.occupied

            return (
              <div
                key={option.port}
                className={`
                  port-option
                  ${isSelected ? 'selected' : ''}
                  ${isDisabled ? 'disabled' : ''}
                `}
                onClick={() => !isDisabled && handlePortSelect(option.port)}
              >
                <div className="port-option-header">
                  <div className="port-option-radio">
                    {isSelected ? '\u29BF' : '\u25CB'}
                  </div>
                  <div className="port-option-title">
                    {option.label} ({option.port})
                    {option.recommended && (
                      <span className="port-option-badge recommended">{'\u2713'} Recommended</span>
                    )}
                    {option.occupied && (
                      <span className="port-option-badge occupied">{'\u26A0\uFE0F'} Occupied</span>
                    )}
                  </div>
                </div>
                <div className="port-option-description">
                  {option.description}
                </div>
              </div>
            )
          })}
        </div>

        {/* Custom port input */}
        <div className="port-option custom" style={{ marginTop: '6px' }}>
          <div className="port-option-header">
            <div className="port-option-radio">
              {!portOptions.find(opt => opt.port === parseInt(tunnelPort)) ? '\u29BF' : '\u25CB'}
            </div>
            <div className="port-option-title">Custom Port</div>
          </div>
          <div className="flex items-center gap-2 mt-2">
            <input
              type="number"
              value={tunnelPort}
              onChange={(e) => {
                setTunnelPort(e.target.value)
                setTunnelPortError(null)
              }}
              className={`
                flex-1 bg-app-bg border rounded px-2 py-1.5 text-xs text-app-text
                focus:outline-none focus:border-app-accent
                ${tunnelPortError ? 'border-red-500' : 'border-app-border'}
              `}
              placeholder="1024-65535"
              min="1024"
              max="65535"
              disabled={tunnelOn}
            />
            <button
              onClick={handleSaveTunnelPort}
              disabled={!portChanged || !portValid || tunnelOn}
              className={`
                px-3 py-1.5 rounded text-xs font-medium transition-colors
                ${portChanged && portValid && !tunnelOn
                  ? 'bg-app-accent text-white hover:bg-app-accent-bright'
                  : 'bg-app-surface text-app-text-dim cursor-not-allowed'
                }
              `}
            >
              Save
            </button>
          </div>
        </div>

        {tunnelPortError && (
          <div className="text-xs text-red-500 mt-2 p-1.5 bg-red-500 bg-opacity-10 rounded border border-red-500 border-opacity-30">
            {'\u26A0\uFE0F'} {tunnelPortError}
          </div>
        )}

        {tunnelOn && portChanged && (
          <div className="text-xs text-app-warning mt-2 p-1.5 bg-app-warning bg-opacity-10 rounded border border-app-warning border-opacity-30">
            {'\u26A0\uFE0F'} Stop tunnel and restart to apply port changes
          </div>
        )}
      </div>

      {/* Info section */}
      <div className="bg-app-surface rounded-lg border border-app-border p-3">
        <div className="text-xs text-app-text-dim leading-relaxed">
          <div className="font-semibold text-app-text mb-2">{'\u{1F4A1}'} Port Information</div>
          <div className="space-y-1">
            <div><span className="text-app-accent">Gateway (11400)</span> - Routes /api to Ollama and /rag to RAG Service</div>
            <div><span className="text-app-accent">Ollama (11434)</span> - Direct LLM access, bypasses Gateway</div>
            <div><span className="text-app-accent">RAG (11435)</span> - Direct embeddings access, bypasses Gateway</div>
          </div>
          <div className="mt-3 text-app-warning">
            {'\u26A0\uFE0F'} Changes require tunnel restart to take effect
          </div>
        </div>
      </div>
    </div>

    {/* Environment Variables Editor */}
    <EnvVarEditor />
    </>
  )
}
