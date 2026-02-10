import type { ServiceStatus } from '../../types/monitor'

interface TunnelTabProps {
  status: ServiceStatus | null
  actionLoading: string | null
  handleAction: (action: string, command: string) => void
  savedTunnelPort: string
  tunnelFileContent: string
  copiedUrl: boolean
  handleCopyUrl: () => void
}

export function TunnelTab({
  status,
  actionLoading,
  handleAction,
  savedTunnelPort,
  tunnelFileContent,
  copiedUrl,
  handleCopyUrl,
}: TunnelTabProps) {
  const tunnelOn = status?.tunnel_running ?? false

  return (
    <div className="flex gap-4 p-4 h-full">
      {/* ===== COLUMN 1: Tunnel Controls ===== */}
      <div className="flex flex-col gap-4 flex-1">
        {/* Tunnel Service Card */}
        <div className={`service-card ${tunnelOn ? 'active' : ''} ${!status?.ollama_running ? 'disabled' : ''}`}>
          <div className="service-icon">{'\u{1F517}'}</div>
          <div className="service-body">
            <div className="service-name">Tunnel</div>
            <div className={`service-status ${tunnelOn ? 'on' : 'off'}`}>
              {tunnelOn
                ? status?.tunnel_url?.startsWith('https://')
                  ? '\u25CF Cloudflared'
                  : `\u25CF Local (${savedTunnelPort})`
                : '\u25CB Desconectado'}
            </div>
            {tunnelOn && status?.tunnel_url?.startsWith('https://') && (
              <div className="tunnel-url-box" onClick={handleCopyUrl} title="Click para copiar">
                <span className="url-text">{status.tunnel_url.replace('https://', '')}</span>
                <span className="copy-icon">{copiedUrl ? '\u2713' : '\u{1F4CB}'}</span>
              </div>
            )}
            {tunnelOn && status?.tunnel_url?.startsWith('https://') && !status.tunnel_url.includes('trycloudflare') && (
              <div className="tunnel-url-pending">{'\u23F3'} Obteniendo URL...</div>
            )}
          </div>
          <button
            className={`action-btn ${tunnelOn ? 'stop' : 'start'}`}
            onClick={() => handleAction(tunnelOn ? 'tunnel-stop' : 'tunnel-start', tunnelOn ? 'stop_tunnel' : 'start_tunnel')}
            disabled={!!actionLoading || !status?.ollama_running}
          >
            {actionLoading?.includes('tunnel') ? '...' : tunnelOn ? '\u25A0' : '\u25B6'}
          </button>
        </div>

        {/* Warning section */}
        {!status?.ollama_running && (
          <div className="bg-app-surface rounded-lg border border-app-warning p-4 text-sm text-app-text-dim">
            {'\u26A0\uFE0F'} Start Ollama first to enable the tunnel
          </div>
        )}
      </div>

      {/* ===== COLUMN 2: File Viewer ===== */}
      <div className="flex flex-col flex-1">
        <div className="bg-app-surface rounded-lg border border-app-border p-4 h-full flex flex-col">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-base">{'\u{1F4C4}'}</span>
            <span className="text-sm font-medium text-app-text">tunnel-url.json</span>
          </div>
          {tunnelFileContent ? (
            <textarea
              readOnly
              value={tunnelFileContent}
              className="flex-1 bg-app-bg text-app-text text-xs font-mono p-3 rounded border border-app-border resize-none focus:outline-none focus:ring-1 focus:ring-app-accent"
              style={{ minHeight: '200px' }}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center text-app-text-dim text-sm">
              No file yet - start tunnel to create
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
