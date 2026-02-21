/**
 * SystemResourcesPanel
 *
 * Single Responsibility: Renders the system resources dashboard — RAM usage bar,
 * CPU info, and running Ollama models with unload controls.
 *
 * Route: /admin/models
 */

'use client';

import {
  Loader2,
  X,
  Cpu,
  HardDrive,
  Activity,
  Zap,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  formatTimeUntil,
  type SystemResources,
  type RunningModelsResponse,
} from '@/lib/api/system';

// ── Helpers ─────────────────────────────────────────────────────────

function getProgressClass(percent: number): string {
  if (percent < 50) return 'mdl-progress-ok';
  if (percent < 75) return 'mdl-progress-warn';
  if (percent < 90) return 'mdl-progress-danger';
  return 'mdl-progress-critical';
}

function getProcessorClass(processor: string): string {
  if (processor === 'gpu') return 'mdl-processor-gpu';
  if (processor === 'partial') return 'mdl-processor-partial';
  return 'mdl-processor-cpu';
}

// ── Component ───────────────────────────────────────────────────────

interface SystemResourcesPanelProps {
  systemResources: SystemResources | null;
  runningModels: RunningModelsResponse | null;
  resourcesLoading: boolean;
  onRefresh: () => void;
  onUnloadModel: (modelName: string) => void;
}

export function SystemResourcesPanel({
  systemResources,
  runningModels,
  resourcesLoading,
  onRefresh,
  onUnloadModel,
}: SystemResourcesPanelProps) {
  return (
    <div className="mdl-resources-panel">
      <div className="mdl-resources-title-row">
        <div className="fi-flex-gap">
          <Activity className="mdl-icon-md fi-text-success" />
          <h3 className="fi-title">Recursos del Sistema</h3>
        </div>
        <Button
          onClick={onRefresh}
          disabled={resourcesLoading}
          variant="ghost"
          size="sm"
          icon={RefreshCw}
          className={resourcesLoading ? 'mdl-spin-svg' : ''}
        >
          Actualizar
        </Button>
      </div>

      {resourcesLoading && !systemResources ? (
        <LoadingState />
      ) : systemResources ? (
        <div className="mdl-resources-body">
          <RamUsageBar memory={systemResources.memory} />
          <CpuInfoRow
            cpuPercent={systemResources.cpu_percent}
            cpuCount={systemResources.cpu_count}
            platform={systemResources.platform}
          />
          {runningModels && (
            <RunningModelsSection
              runningModels={runningModels}
              onUnload={onUnloadModel}
            />
          )}
        </div>
      ) : (
        <p className="mdl-no-resources">No se pudieron cargar los recursos del sistema</p>
      )}
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────

function LoadingState() {
  return (
    <div className="mdl-resources-loading">
      <Loader2 className="mdl-resources-loading-icon" />
      <span className="mdl-resources-loading-text">Cargando recursos...</span>
    </div>
  );
}

function RamUsageBar({ memory }: { memory: SystemResources['memory'] }) {
  return (
    <div>
      <div className="mdl-ram-header">
        <div className="fi-flex-gap">
          <HardDrive className="mdl-icon-sm" />
          <span className="mdl-ram-label">Memoria RAM</span>
        </div>
        <span className="mdl-ram-value">
          {memory.used_gb.toFixed(1)}GB / {memory.total_gb.toFixed(1)}GB
        </span>
      </div>
      <div className="mdl-progress-track">
        <div
          className={`mdl-progress-bar ${getProgressClass(memory.percent_used)}`}
          style={{ width: `${memory.percent_used}%` }}
        />
      </div>
      <div className="mdl-progress-labels">
        <span>{memory.available_gb.toFixed(1)}GB disponible</span>
        <span>{memory.percent_used.toFixed(0)}% usado</span>
      </div>
    </div>
  );
}

function CpuInfoRow({
  cpuPercent,
  cpuCount,
  platform,
}: {
  cpuPercent: number;
  cpuCount: number;
  platform: string;
}) {
  return (
    <div className="mdl-cpu-row">
      <div className="fi-flex-gap">
        <Cpu className="mdl-icon-sm" />
        <span className="fi-text">CPU: {cpuPercent.toFixed(0)}%</span>
        <span className="mdl-text-muted">({cpuCount} cores)</span>
      </div>
      <span className="mdl-text-muted">{platform}</span>
    </div>
  );
}

function RunningModelsSection({
  runningModels,
  onUnload,
}: {
  runningModels: RunningModelsResponse;
  onUnload: (name: string) => void;
}) {
  return (
    <div className="mdl-running-section">
      <div className="mdl-ollama-header">
        <div className="fi-flex-gap">
          <Zap className="mdl-icon-sm fi-text-warning" />
          <span className="mdl-ollama-label">Modelos en Memoria (Ollama)</span>
        </div>
        {runningModels.ollama_available ? (
          <span className="mdl-ollama-active">
            <span className="mdl-status-dot" />
            Ollama activo
          </span>
        ) : (
          <span className="mdl-ollama-inactive">Ollama no disponible</span>
        )}
      </div>

      {runningModels.models.length === 0 ? (
        <p className="mdl-no-models">
          Sin modelos cargados • RAM libre para cargar modelos
        </p>
      ) : (
        <div className="fi-stack-sm">
          {runningModels.models.map((model) => (
            <div key={model.model_id} className="mdl-running-card">
              <div className="fi-flex-gap-md">
                <span className={getProcessorClass(model.processor)}>
                  {model.processor.toUpperCase()}
                </span>
                <span className="mdl-model-name">{model.name}</span>
                <span className="fi-text-xs-muted">{model.size_gb}GB</span>
              </div>
              <div className="fi-flex-gap">
                <span className="fi-text-xs-muted">
                  {formatTimeUntil(model.until)}
                </span>
                <Button
                  onClick={() => onUnload(model.name)}
                  variant="ghost"
                  size="xs"
                  icon={X}
                  title="Descargar de memoria"
                  className="mdl-unload-btn"
                />
              </div>
            </div>
          ))}
          <div className="mdl-running-total">
            Total en memoria: {runningModels.total_loaded_gb.toFixed(1)}GB
          </div>
        </div>
      )}
    </div>
  );
}
