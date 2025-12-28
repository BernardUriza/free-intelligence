/**
 * AdvancedMetrics Component
 *
 * Expandable panel with performance metrics, chunk timeline, and activity logs.
 *
 * Features:
 * - Performance metrics grid (latency, WPM, completion rate)
 * - Chunk timeline visualization with tooltips
 * - Activity logs with scrollable view
 * - Backend health indicator
 * - Collapsible UI
 *
 * Extracted from ConversationCapture (Phase 7)
 */

import { useState } from 'react';
import { BarChart3, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface ChunkStatus {
  index: number;
  status: 'uploading' | 'pending' | 'processing' | 'completed' | 'failed' | 'unresolved';
  startTime?: number;
  endTime?: number;
  latency?: number;
  transcript?: string | null;
  error?: string;
  provider?: string;
  resolution_time_seconds?: number;
  retry_attempts?: number;
  polling_attempts?: number;
  confidence?: number;
  duration?: number;
}

interface AdvancedMetricsProps {
  chunkStatuses: ChunkStatus[];
  avgLatency: number;
  wpm: number;
  backendHealth: 'healthy' | 'degraded' | 'down';
  activityLogs: string[];
}

export function AdvancedMetrics({
  chunkStatuses,
  avgLatency,
  wpm,
  backendHealth,
  activityLogs,
}: AdvancedMetricsProps) {
  const [showAdvancedMetrics, setShowAdvancedMetrics] = useState(false);

  const completed = chunkStatuses.filter(c => c.status === 'completed').length;
  const failed = chunkStatuses.filter(c => c.status === 'failed').length;

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 animate-in">
      <Button
        onClick={() => setShowAdvancedMetrics(!showAdvancedMetrics)}
        variant="ghost"
        fullWidth
        className="px-6 py-4 flex items-center justify-between"
      >
        <div className="fi-flex-gap-md">
          <BarChart3 className="fi-icon-md fi-icon-cyan" />
          <h3 className="fi-title">Métricas Avanzadas</h3>
          {/* Backend Health Badge */}
          <span className={`px-2 py-0.5 rounded-full fi-text-xs-medium ${
            backendHealth === 'healthy' ? 'bg-emerald-500/20 fi-text-success' :
            backendHealth === 'degraded' ? 'bg-yellow-500/20 text-yellow-400' :
            'bg-red-500/20 fi-text-error'
          }`}>
            {backendHealth === 'healthy' ? '🟢 Backend OK' :
             backendHealth === 'degraded' ? '🟡 Degradado' : '🔴 Down'}
          </span>
        </div>
        <ChevronDown className={`fi-icon-md fi-icon-slate transition-transform ${showAdvancedMetrics ? 'rotate-180' : ''}`} />
      </Button>

      {showAdvancedMetrics && (
        <div className="px-6 pb-6 space-y-6 animate-in fade-in">
          {/* Performance Metrics Grid */}
          <div className="grid grid-cols-4 gap-3">
            <div className="fi-card-dark-sm">
              <div className="fi-text-xs mb-1">Latencia Promedio</div>
              <div className="text-xl font-bold fi-text-info">
                {avgLatency > 0 ? `${(avgLatency / 1000).toFixed(1)}s` : '--'}
              </div>
            </div>
            <div className="fi-card-dark-sm">
              <div className="fi-text-xs mb-1">WPM</div>
              <div className="text-xl font-bold fi-text-success">{wpm || '--'}</div>
            </div>
            <div className="fi-card-dark-sm">
              <div className="fi-text-xs mb-1">Completados</div>
              <div className="text-xl font-bold fi-text-purple">
                {completed}/{chunkStatuses.length}
              </div>
            </div>
            <div className="fi-card-dark-sm">
              <div className="fi-text-xs mb-1">Fallidos</div>
              <div className="text-xl font-bold fi-text-error">
                {failed}
              </div>
            </div>
          </div>

          {/* Chunk Timeline Visualization */}
          <div>
            <div className="text-sm font-medium fi-text mb-3">Timeline de Chunks</div>
            <div className="flex flex-wrap gap-1.5">
              {chunkStatuses.map((chunk) => (
                <div
                  key={chunk.index}
                  className={`relative group w-8 h-8 rounded flex items-center justify-center fi-text-xs-medium transition-all ${
                    chunk.status === 'uploading' ? 'bg-blue-500/30 text-blue-300 animate-pulse' :
                    chunk.status === 'pending' ? 'bg-yellow-500/30 text-yellow-300' :
                    chunk.status === 'processing' ? 'bg-cyan-500/30 text-cyan-300 animate-pulse' :
                    chunk.status === 'completed' ? 'bg-emerald-500/30 text-emerald-300' :
                    'bg-red-500/30 text-red-300'
                  }`}
                  title={`Chunk ${chunk.index}: ${chunk.status}${chunk.latency ? ` (${(chunk.latency / 1000).toFixed(1)}s)` : ''}`}
                >
                  {chunk.index}
                  {/* Tooltip on hover */}
                  <div className="fi-tooltip">
                    <div>Chunk {chunk.index}</div>
                    <div className="text-slate-400">{chunk.status}</div>
                    {chunk.latency && <div className="fi-text-info">{(chunk.latency / 1000).toFixed(1)}s</div>}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-4 mt-3 fi-text-xs">
              <div className="fi-flex-gap-sm">
                <div className="w-3 h-3 rounded bg-blue-500/30" />
                <span>Uploading</span>
              </div>
              <div className="fi-flex-gap-sm">
                <div className="w-3 h-3 rounded bg-yellow-500/30" />
                <span>Pending</span>
              </div>
              <div className="fi-flex-gap-sm">
                <div className="w-3 h-3 rounded bg-cyan-500/30" />
                <span>Processing</span>
              </div>
              <div className="fi-flex-gap-sm">
                <div className="w-3 h-3 rounded bg-emerald-500/30" />
                <span>Completed</span>
              </div>
              <div className="fi-flex-gap-sm">
                <div className="w-3 h-3 rounded bg-red-500/30" />
                <span>Failed</span>
              </div>
            </div>
          </div>

          {/* Activity Logs */}
          {activityLogs.length > 0 && (
            <div>
              <div className="text-sm font-medium fi-text mb-3">Registro de Actividad</div>
              <div className="bg-slate-900/50 rounded-lg border border-slate-700 p-3 font-mono text-xs max-h-48 overflow-y-auto">
                {activityLogs.map((log, idx) => (
                  <div key={idx} className="text-slate-400 py-1 border-b border-slate-800 last:border-0">
                    {log}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
