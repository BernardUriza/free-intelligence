'use client';

import { Activity, Cpu, HardDrive, Loader2, RefreshCw, X, Zap } from 'lucide-react';
import { AdminAlert, AdminButton } from '../admin-kit';
import { formatTimeUntil, usageLevel } from './format';
import { FI_MODEL_CATALOG_ROOT_CLASS, useModelCatalogStyle } from './modelCatalogStyle';
import type { SystemResourcesState } from './useSystemResources';

export type SystemResourcesPanelProps = Pick<
  SystemResourcesState,
  'resources' | 'running' | 'loading' | 'error' | 'refresh' | 'unload' | 'unloading'
>;

export function SystemResourcesPanel({ resources, running, loading, error, refresh, unload, unloading }: SystemResourcesPanelProps) {
  useModelCatalogStyle();
  return (
    <section className={`${FI_MODEL_CATALOG_ROOT_CLASS} fi-mc-panel`} aria-label="Recursos del sistema">
      <div className="fi-mc-panel-head">
        <h3 className="fi-mc-title">
          <Activity size={20} aria-hidden="true" />
          Recursos del sistema
        </h3>
        <AdminButton variant="ghost" icon={RefreshCw} loading={loading} disabled={loading} onClick={() => void refresh()}>
          Actualizar
        </AdminButton>
      </div>

      {error ? <AdminAlert>{error}</AdminAlert> : null}

      {!resources ? (
        loading ? (
          <p className="fi-mc-inline fi-mc-muted" role="status">
            <Loader2 size={16} className="fi-admin-spin" aria-hidden="true" />
            Cargando recursos...
          </p>
        ) : null
      ) : (
        <>
          <div>
            <div className="fi-mc-row-between">
              <span className="fi-mc-inline">
                <HardDrive size={16} aria-hidden="true" className="fi-mc-muted" />
                Memoria RAM
              </span>
              <span className="fi-mc-mono">
                {resources.memory.used_gb.toFixed(1)}GB / {resources.memory.total_gb.toFixed(1)}GB
              </span>
            </div>
            <div
              className="fi-mc-meter"
              data-level={usageLevel(resources.memory.percent_used)}
              role="meter"
              aria-label="Memoria RAM usada"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(resources.memory.percent_used)}
            >
              <div style={{ width: `${Math.min(100, resources.memory.percent_used)}%` }} />
            </div>
            <div className="fi-mc-row-between fi-mc-small">
              <span>{resources.memory.available_gb.toFixed(1)}GB disponible</span>
              <span>{resources.memory.percent_used.toFixed(0)}% usado</span>
            </div>
          </div>

          <div className="fi-mc-row-between" style={{ marginTop: '0.75rem' }}>
            <span className="fi-mc-inline">
              <Cpu size={16} aria-hidden="true" className="fi-mc-muted" />
              CPU: {resources.cpu_percent.toFixed(0)}%<span className="fi-mc-muted">({resources.cpu_count} cores)</span>
            </span>
            <span className="fi-mc-muted">{resources.platform}</span>
          </div>

          {running ? (
            <div className="fi-mc-section">
              <div className="fi-mc-row-between">
                <span className="fi-mc-inline">
                  <Zap size={16} aria-hidden="true" className="fi-mc-muted" />
                  Modelos en memoria (Ollama)
                </span>
                {running.ollama_available ? (
                  <span className="fi-mc-inline fi-mc-small">
                    <span className="fi-mc-dot" aria-hidden="true" />
                    Ollama activo
                  </span>
                ) : (
                  <span className="fi-mc-small">Ollama no disponible</span>
                )}
              </div>
              {running.models.length === 0 ? (
                <p className="fi-mc-small">Sin modelos cargados · RAM libre para cargar modelos</p>
              ) : (
                <ul className="fi-mc-running" style={{ listStyle: 'none', padding: 0 }}>
                  {running.models.map((model) => (
                    <li key={model.model_id} className="fi-mc-running-item">
                      <span className="fi-mc-inline">
                        <span className="fi-mc-proc" data-processor={model.processor}>
                          {model.processor.toUpperCase()}
                        </span>
                        <span className="fi-mc-mono">{model.name}</span>
                        <span className="fi-mc-small">{model.size_gb}GB</span>
                      </span>
                      <span className="fi-mc-inline">
                        <span className="fi-mc-small">{formatTimeUntil(model.until)}</span>
                        <AdminButton
                          variant="ghost"
                          iconOnly
                          tone="danger"
                          icon={X}
                          loading={unloading === model.name}
                          disabled={unloading === model.name}
                          aria-label={`Descargar ${model.name} de memoria`}
                          title="Descargar de memoria"
                          onClick={() => void unload(model.name)}
                        />
                      </span>
                    </li>
                  ))}
                  <li className="fi-mc-small">Total en memoria: {running.total_loaded_gb.toFixed(1)}GB</li>
                </ul>
              )}
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
