'use client';

import { useState, useEffect, useRef } from 'react';
import { Brain, Monitor, Cloud } from 'lucide-react';
import { api } from '@/lib/api/client';
import { ROUTES } from '@/lib/api/routes';

interface LLMStatusResponse {
  status: 'online' | 'offline' | 'checking';
  url: string;
  is_tunnel: boolean;
  tunnel_info: {
    tunnel_url?: string;
    hostname?: string;
    updated_at?: string;
  } | null;
  models: string[];
  latency_ms: number | null;
  last_check: string;
  priority: 'tunnel' | 'local_fallback';
}

export function SystemStatus() {
  const [status, setStatus] = useState<LLMStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isOpen, setIsOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await api.get<LLMStatusResponse>(`${ROUTES.system}/llm-status`);
        setStatus(data);
      } catch {
        setStatus({
          status: 'offline',
          url: 'error',
          is_tunnel: false,
          tunnel_info: null,
          models: [],
          latency_ms: null,
          last_check: new Date().toISOString(),
          priority: 'local_fallback',
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchStatus();
    const intervalId = setInterval(fetchStatus, 30000);
    return () => clearInterval(intervalId);
  }, []);

  // Close panel when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const statusConfig = {
    checking: { color: 'bg-yellow-500', ring: 'ring-yellow-500/30' },
    online: { color: 'bg-green-500', ring: 'ring-green-500/30' },
    offline: { color: 'bg-red-500', ring: 'ring-red-500/30' },
  };

  const currentStatus = isLoading ? 'checking' : (status?.status || 'offline');
  const { color, ring } = statusConfig[currentStatus as keyof typeof statusConfig];

  const formatDate = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString('es-MX', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return 'N/A';
    }
  };

  return (
    <div className="relative" ref={panelRef}>
      {/* Status Brain Icon - Clickeable */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`relative flex items-center justify-center w-6 h-6 rounded-full
          ${currentStatus === 'online' ? 'text-green-400' : currentStatus === 'checking' ? 'text-yellow-400' : 'text-red-400'}
          hover:ring-2 ${ring} transition-all cursor-pointer group`}
        aria-label="Estado del LLM"
      >
        {/* Brain icon with pulsating glow */}
        <Brain
          className={`w-4 h-4 relative z-10 ${isLoading || currentStatus === 'online' ? 'animate-pulse' : ''}`}
        />
        {/* Sparkle effects for online status */}
        {currentStatus === 'online' && (
          <>
            <span className="absolute w-1 h-1 bg-green-400 rounded-full animate-ping top-0 right-0.5" />
            <span className="ui-status-sparkle top-1 left-0 animation-delay-200" />
            <span className="ui-status-sparkle bottom-0.5 right-1 animation-delay-500" />
          </>
        )}
        {/* Glow ring effect */}
        <span className={`absolute inset-0 rounded-full ${color} opacity-20 ${currentStatus === 'online' ? 'animate-ping' : ''}`} />
      </button>

      {/* Expandable Panel */}
      {isOpen && status && (
        <div className="ui-status-panel">
          {/* Header */}
          <div className={`ui-status-header-inner ${status.status === 'online' ? 'bg-green-900/30' : 'bg-red-900/30'}`}>
            <div className="ui-status-header">
              <span className="ui-status-label-sm">
                LLM Status
              </span>
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                status.status === 'online'
                  ? 'bg-green-500/20 text-green-400'
                  : 'bg-red-500/20 text-red-400'
              }`}>
                {status.status === 'online' ? 'Online' : 'Offline'}
              </span>
            </div>
          </div>

          {/* Content */}
          <div className="ui-status-content">
            {/* URL & Priority */}
            <div>
              <div className="ui-status-section-label">Conexión</div>
              <div className="ui-status-code-box">
                {status.url}
              </div>
              <div className="ui-status-badge-row">
                <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] ${
                  status.is_tunnel
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'bg-slate-600/50 text-slate-400'
                }`}>
                  {status.is_tunnel ? (
                    <><Cloud className="w-3 h-3" /> Tunnel</>
                  ) : (
                    <><Monitor className="w-3 h-3" /> Local</>
                  )}
                </span>
                <span className="text-slate-500">
                  Prioridad: {status.priority === 'tunnel' ? 'Windows GPU' : 'Mac Fallback'}
                </span>
              </div>
            </div>

            {/* Tunnel Info (if available) */}
            {status.tunnel_info && (
              <div>
                <div className="ui-status-section-label">Tunnel Info</div>
                <div className="ui-status-info-box">
                  {status.tunnel_info.hostname && (
                    <div className="ui-status-info-row">
                      <span className="ui-status-info-label">Host:</span>
                      <span className="text-slate-300">{status.tunnel_info.hostname}</span>
                    </div>
                  )}
                  {status.tunnel_info.updated_at && (
                    <div className="ui-status-info-row">
                      <span className="ui-status-info-label">Actualizado:</span>
                      <span className="text-slate-300">{formatDate(status.tunnel_info.updated_at)}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Models */}
            {status.models.length > 0 && (
              <div>
                <div className="ui-status-section-label">Modelos ({status.models.length})</div>
                <div className="flex flex-wrap gap-1">
                  {status.models.map((model) => (
                    <span
                      key={model}
                      className="ui-status-model-tag"
                    >
                      {model}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Metrics */}
            <div className="ui-status-metrics-row">
              <div className="flex items-center gap-3">
                {status.latency_ms !== null && (
                  <div className="flex items-center gap-1">
                    <span className="ui-status-info-label">Latencia:</span>
                    <span className={`font-mono ${
                      status.latency_ms < 100 ? 'text-green-400' :
                      status.latency_ms < 500 ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      {status.latency_ms}ms
                    </span>
                  </div>
                )}
              </div>
              <div className="ui-status-info-label">
                {formatDate(status.last_check)}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SystemStatus;
