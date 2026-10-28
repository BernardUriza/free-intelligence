'use client';

import { useId } from 'react';
import {
  AlertCircle,
  Check,
  CheckCircle,
  Cpu,
  DatabaseZap,
  Download,
  HardDrive,
  Inbox,
  Keyboard,
  Library,
  Loader2,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
  X,
  type LucideIcon,
} from 'lucide-react';
import { AdminAlert, AdminButton } from '../admin-kit';
import { ModelSheet } from './ModelSheet';
import { CATALOG_SIZE_OPTIONS, CATALOG_SOURCES, QUANT_INFO, SOURCE_INFO, formatBytes } from './format';
import { ProviderLogo } from './ProviderLogo';
import { useCatalogKeyboardNavigation } from './useCatalogKeyboardNavigation';
import { useModelCatalog, type CatalogFilter, type CatalogSourceState } from './useModelCatalog';
import type { CatalogModel, CatalogSource, ModelCatalogConfirm, ModelCatalogNotify, ModelCatalogStore } from './types';

export interface ModelCatalogDrawerProps {
  open: boolean;
  onClose: () => void;
  store: Pick<ModelCatalogStore, 'listCatalog' | 'installCatalogModel' | 'removeCatalogModel' | 'createModel'>;
  onModelsChanged?: () => void;
  confirm?: ModelCatalogConfirm;
  notify?: ModelCatalogNotify;
  /** Sources whose installed models can be deleted from disk. aurity's backend only removes from Ollama. */
  removableSources?: readonly CatalogSource[];
}

interface Tab {
  key: CatalogFilter;
  label: string;
  icon?: LucideIcon;
  count?: number;
}

export function ModelCatalogDrawer({
  open,
  onClose,
  store,
  onModelsChanged,
  confirm,
  notify,
  removableSources = ['ollama'],
}: ModelCatalogDrawerProps) {
  const titleId = useId();
  const catalog = useModelCatalog(store, { open, onModelsChanged, confirm, notify });
  const { selectedIndex, listRef, searchRef } = useCatalogKeyboardNavigation({
    open,
    models: catalog.displayedModels,
    installing: catalog.installing,
    onInstall: catalog.install,
  });
  if (!open) return null;

  const tabs: Tab[] = [
    { key: 'all', label: 'Todos', icon: Library },
    { key: 'installed', label: 'Instalados', icon: CheckCircle, count: catalog.installedCount },
    { key: 'gpt4all', label: 'GPT4All' },
    { key: 'huggingface', label: 'HF' },
    { key: 'ollama', label: 'Ollama' },
  ];
  const row = (model: CatalogModel, extra: { featured?: boolean; selected?: boolean; index?: number }) => (
    <CatalogModelRow
      key={model.id}
      model={model}
      featured={extra.featured}
      selected={extra.selected}
      navigable={extra.index !== undefined}
      progress={catalog.installing[model.id]}
      error={catalog.installErrors[model.id]}
      removable={removableSources.includes(model.source)}
      onInstall={() => void catalog.install(model)}
      onRemove={() => void catalog.remove(model)}
    />
  );

  return (
    <ModelSheet
      onDismiss={onClose}
      labelledBy={titleId}
      placement="side"
      bodyRef={listRef}
      header={
        <>
          <div className="fi-admin-head-row">
            <div>
              <h2 id={titleId} className="fi-mc-title">
                <Library size={22} aria-hidden="true" />
                Catálogo de modelos
              </h2>
              <p className="fi-mc-subtitle">
                {catalog.loading
                  ? `Cargando... ${catalog.allModels.length} modelos`
                  : `${catalog.allModels.length} modelos · ${catalog.installedCount} instalados`}
              </p>
            </div>
            <AdminButton variant="ghost" iconOnly icon={X} aria-label="Cerrar" onClick={onClose} />
          </div>
          <SourceStatusBar states={catalog.sourceStates} />
          <div className="fi-mc-toolbar">
            <div className="fi-mc-search">
              <Search size={16} aria-hidden="true" />
              <input
                ref={searchRef}
                type="search"
                className="fi-mc-input"
                aria-label="Buscar modelos"
                placeholder="Buscar modelos... (presiona /)"
                value={catalog.searchQuery}
                onChange={(e) => catalog.setSearchQuery(e.target.value)}
              />
            </div>
            <select
              className="fi-mc-input"
              aria-label="Tamaño máximo"
              value={catalog.maxSizeGb?.toString() ?? ''}
              onChange={(e) => catalog.setMaxSizeGb(e.target.value ? Number(e.target.value) : undefined)}
            >
              {CATALOG_SIZE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <AdminButton
              iconOnly
              icon={RefreshCw}
              loading={catalog.loading}
              disabled={catalog.loading}
              aria-label="Recargar catálogo"
              title="Recargar catálogo"
              onClick={catalog.reload}
            />
            <AdminButton
              iconOnly
              icon={DatabaseZap}
              loading={catalog.syncing}
              disabled={catalog.loading || catalog.syncing || catalog.installedCount === 0}
              aria-label="Sincronizar modelos instalados"
              title="Sincronizar modelos instalados al registro"
              onClick={() => void catalog.syncInstalled()}
            />
          </div>
          <div className="fi-mc-tabs" role="tablist" aria-label="Fuente">
            {tabs.map((tab) => (
              <AdminButton
                key={tab.key}
                role="tab"
                aria-selected={catalog.filter === tab.key}
                className="fi-mc-tab"
                icon={tab.icon}
                onClick={() => catalog.setFilter(tab.key)}
              >
                {tab.icon ? null : <ProviderLogo provider={tab.key} size={16} />}
                {tab.label}
                {tab.count !== undefined ? <span className="fi-mc-count">{tab.count}</span> : null}
              </AdminButton>
            ))}
          </div>
        </>
      }
      footer={
        <div className="fi-mc-keys">
          <span className="fi-mc-inline">
            <Keyboard size={14} aria-hidden="true" />
            ↑↓ navegar · Enter instalar · Esc cerrar
          </span>
          <span>/ para buscar</span>
        </div>
      }
    >
      {catalog.loading && catalog.models.length === 0 ? (
        <div className="fi-mc-list" role="status" aria-label="Cargando catálogo">
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className="fi-mc-skel" />
          ))}
        </div>
      ) : null}

      {catalog.allErrors && !catalog.loading ? (
        <AdminAlert
          action={
            <AdminButton variant="danger" onClick={catalog.reload}>
              Reintentar
            </AdminButton>
          }
        >
          Error al cargar todas las fuentes
        </AdminAlert>
      ) : null}

      {catalog.featuredModels.length > 0 ? (
        <section>
          <h3 className="fi-mc-section-title" data-tone="featured">
            <Sparkles size={14} aria-hidden="true" />
            DESTACADOS
          </h3>
          <ul className="fi-mc-list">{catalog.featuredModels.map((m) => row(m, { featured: true }))}</ul>
        </section>
      ) : null}

      {catalog.displayedModels.length > 0 ? (
        <section>
          {catalog.filter === 'all' && !catalog.searchQuery ? (
            <h3 className="fi-mc-section-title">TODOS LOS MODELOS ({catalog.displayedModels.length})</h3>
          ) : null}
          <ul className="fi-mc-list">
            {catalog.displayedModels.map((m, index) => row(m, { index, selected: index === selectedIndex }))}
          </ul>
        </section>
      ) : null}

      {!catalog.loading && catalog.allLoaded && catalog.models.length === 0 && !catalog.allErrors ? (
        <div className="fi-mc-empty">
          {catalog.filter === 'installed' ? <Inbox size={44} aria-hidden="true" /> : <Search size={44} aria-hidden="true" />}
          <h3>{catalog.filter === 'installed' ? 'No hay modelos instalados' : 'Sin resultados'}</h3>
          <p>
            {catalog.filter === 'installed'
              ? 'Explora el catálogo para instalar modelos.'
              : catalog.searchQuery
                ? `No hay modelos que coincidan con "${catalog.searchQuery}".`
                : 'Intenta con otros filtros.'}
          </p>
        </div>
      ) : null}
    </ModelSheet>
  );
}

function SourceStatusBar({ states }: { states: Record<CatalogSource, CatalogSourceState> }) {
  return (
    <div className="fi-mc-sources">
      {CATALOG_SOURCES.map((source) => {
        const state = states[source];
        return (
          <span key={source} className="fi-mc-chip" data-status={state.status} title={state.error}>
            {state.status === 'loading' ? <Loader2 size={14} className="fi-admin-spin" aria-hidden="true" /> : null}
            {state.status === 'error' ? <AlertCircle size={14} aria-hidden="true" /> : null}
            <ProviderLogo provider={source} size={14} />
            {SOURCE_INFO[source].label}
            {state.status === 'loading' ? <span className="fi-mc-count">Cargando...</span> : null}
            {state.status === 'loaded' ? <span className="fi-mc-count">{state.models.length}</span> : null}
            {state.status === 'error' ? <span className="fi-mc-count">Error</span> : null}
          </span>
        );
      })}
    </div>
  );
}

export interface CatalogModelRowProps {
  model: CatalogModel;
  /** Download percent while installing; undefined when idle. */
  progress?: number;
  error?: string;
  featured?: boolean;
  selected?: boolean;
  navigable?: boolean;
  removable?: boolean;
  onInstall: () => void;
  onRemove: () => void;
}

export function CatalogModelRow({
  model,
  progress,
  error,
  featured = false,
  selected = false,
  navigable = false,
  removable = false,
  onInstall,
  onRemove,
}: CatalogModelRowProps) {
  const installing = progress !== undefined;
  const percent = Math.round(progress ?? 0);
  return (
    <li
      className="fi-mc-row"
      data-catalog-row={navigable ? '' : undefined}
      data-featured={featured}
      data-installed={model.is_installed}
      data-selected={selected}
      aria-label={model.name}
    >
      <span title={SOURCE_INFO[model.source]?.label}>
        <ProviderLogo provider={model.source} size={24} />
      </span>
      <div className="fi-mc-row-info">
        <div className="fi-mc-inline" style={{ maxWidth: '100%' }}>
          <span className="fi-mc-row-name">{model.name}</span>
          {model.is_installed ? (
            <span className="fi-mc-badge" data-tone="installed">
              <Check size={12} aria-hidden="true" />
              Instalado
            </span>
          ) : featured ? (
            <span className="fi-mc-badge" data-tone="featured">
              Popular
            </span>
          ) : null}
        </div>
        <div className="fi-mc-row-meta">
          <span className="fi-mc-inline">
            <HardDrive size={12} aria-hidden="true" />
            {formatBytes(model.size_bytes)}
          </span>
          {model.ram_required_gb ? (
            <span className="fi-mc-inline">
              <Cpu size={12} aria-hidden="true" />
              {model.ram_required_gb.toFixed(1)} GB
            </span>
          ) : null}
          <span>{QUANT_INFO[model.quantization]?.label ?? model.quantization}</span>
          {model.parameters ? <span>{model.parameters}</span> : null}
        </div>
        {installing ? (
          <>
            <div
              className="fi-mc-meter"
              data-tone="catalog"
              role="progressbar"
              aria-label={`Descarga de ${model.name}`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={percent}
            >
              <div style={{ width: `${percent}%` }} />
            </div>
            <span className="fi-mc-small">Instalando... {percent}%</span>
          </>
        ) : null}
        {error ? (
          <p className="fi-mc-row-error" role="alert">
            {error}
          </p>
        ) : null}
      </div>
      {installing ? (
        <Loader2 size={20} className="fi-admin-spin" aria-hidden="true" />
      ) : model.is_installed ? (
        removable ? (
          <AdminButton
            variant="ghost"
            iconOnly
            tone="danger"
            icon={Trash2}
            aria-label={`Eliminar ${model.name}`}
            title="Eliminar"
            onClick={onRemove}
          />
        ) : null
      ) : (
        <AdminButton variant="primary" icon={Download} aria-label={`Instalar ${model.name}`} onClick={onInstall}>
          Instalar
        </AdminButton>
      )}
    </li>
  );
}
