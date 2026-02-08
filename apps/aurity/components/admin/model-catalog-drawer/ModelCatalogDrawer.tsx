'use client';

/**
 * ModelCatalogDrawer Component
 *
 * A slide-over drawer for browsing and installing models from
 * GPT4All, HuggingFace, and Ollama catalogs.
 */

import {
  X,
  Search,
  RefreshCw,
  Sparkles,
  Keyboard,
  DatabaseZap,
  AlertCircle,
  Library,
  Inbox,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';

import type { ModelCatalogDrawerProps } from './types';
import { getFilterTabs, SIZE_OPTIONS } from './constants';
import { useModelCatalog, useKeyboardNavigation } from './hooks';
import {
  ModelRow,
  ModelRowSkeleton,
  SourceLoadingStatus,
  FilterTabs,
} from './components';

export function ModelCatalogDrawer({
  isOpen,
  onClose,
  onModelInstalled,
}: ModelCatalogDrawerProps) {
  const {
    sourceStates,
    sourceFilter,
    searchQuery,
    maxSizeGb,
    installingModels,
    isSyncing,
    allModels,
    models,
    displayedModels,
    featuredModels,
    installedCount,
    loading,
    allLoaded,
    allErrors,
    setSourceFilter,
    setSearchQuery,
    setMaxSizeGb,
    loadCatalog,
    handleInstall,
    handleDelete,
    syncInstalledModels,
  } = useModelCatalog({ isOpen, onModelInstalled });

  const { selectedIndex, listRef, searchInputRef } = useKeyboardNavigation({
    isOpen,
    onClose,
    displayedModels,
    installingModels,
    onInstall: handleInstall,
  });

  const filterTabs = getFilterTabs(installedCount);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fi-modal-backdrop z-40 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        className={`admin-catalog-drawer ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
        role="dialog"
        aria-modal="true"
        aria-label="Catálogo de modelos"
      >
        {/* Header */}
        <div className="flex-shrink-0 px-6 py-4 fi-border-bottom bg-slate-900/95">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="fi-title-xl flex items-center gap-2">
                <Library className="w-7 h-7 text-purple-400" strokeWidth={1.5} />
                Catálogo de Modelos
              </h2>
              <p className="fi-subtitle mt-0.5">
                {loading
                  ? `Cargando... ${allModels.length} modelos`
                  : `${allModels.length} modelos · ${installedCount} instalados`}
              </p>
            </div>
            <Button onClick={onClose} variant="ghost" size="sm" icon={X} aria-label="Cerrar" />
          </div>

          <SourceLoadingStatus sourceStates={sourceStates} />

          {/* Search & Filters */}
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                ref={searchInputRef}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Buscar modelos... (presiona /)"
                className="pl-10 pr-4 bg-slate-800 border-slate-700"
              />
            </div>
            <Select
              value={maxSizeGb?.toString() || ''}
              onValueChange={(val) => setMaxSizeGb(val ? Number(val) : undefined)}
            >
              <SelectTrigger className="w-28">
                <SelectValue placeholder="Tamaño" />
              </SelectTrigger>
              <SelectContent>
                {SIZE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              onClick={loadCatalog}
              disabled={loading}
              variant="secondary"
              size="sm"
              icon={RefreshCw}
              className={loading ? '[&_svg]:animate-spin' : ''}
              title="Recargar catálogo"
              aria-label="Recargar catálogo"
            />
            <Button
              onClick={syncInstalledModels}
              disabled={loading || isSyncing || allModels.filter((m) => m.is_installed).length === 0}
              variant="outline"
              size="sm"
              icon={DatabaseZap}
              className={`admin-catalog-sync-btn ${isSyncing ? '[&_svg]:animate-pulse' : ''}`}
              title="Sincronizar modelos instalados a Base de Datos"
              aria-label="Sincronizar modelos"
            />
          </div>

          <FilterTabs
            tabs={filterTabs}
            activeFilter={sourceFilter}
            onFilterChange={setSourceFilter}
          />
        </div>

        {/* Content */}
        <div ref={listRef} className="flex-1 overflow-y-auto px-4 py-4">
          {/* Skeleton Loading */}
          {loading && models.length === 0 && (
            <div className="fi-stack-md">
              <div className="flex items-center gap-2 mb-3 px-1">
                <Sparkles className="w-4 h-4 text-slate-600" />
                <div className="h-4 w-24 bg-slate-700 rounded animate-pulse" />
              </div>
              {[...Array(5)].map((_, i) => (
                <ModelRowSkeleton key={i} />
              ))}
            </div>
          )}

          {/* All Sources Error */}
          {allErrors && !loading && (
            <div className="fi-empty-state py-16">
              <div className="p-4 bg-red-950/30 border border-red-800 rounded-lg max-w-sm text-center">
                <AlertCircle className="w-8 h-8 fi-text-error mx-auto mb-2" />
                <p className="text-red-300 text-sm">Error al cargar todas las fuentes</p>
                <Button onClick={loadCatalog} variant="danger" size="sm" className="mt-3">
                  Reintentar
                </Button>
              </div>
            </div>
          )}

          {/* Models List */}
          {models.length > 0 && (
            <>
              {/* Featured Section */}
              {sourceFilter === 'all' && !searchQuery && featuredModels.length > 0 && (
                <div className="mb-6">
                  <div className="flex items-center gap-2 mb-3 px-1">
                    <Sparkles className="w-4 h-4 fi-text-warning" />
                    <h3 className="text-sm font-semibold fi-text-warning">DESTACADOS</h3>
                  </div>
                  <div className="space-y-2">
                    {featuredModels.map((model) => (
                      <ModelRow
                        key={model.id}
                        model={model}
                        isInstalling={model.id in installingModels}
                        installProgress={installingModels[model.id] || 0}
                        onInstall={() => handleInstall(model)}
                        onDelete={() => handleDelete(model)}
                        featured
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* All Models */}
              {displayedModels.length > 0 && (
                <div>
                  {sourceFilter === 'all' && !searchQuery && (
                    <div className="flex items-center gap-2 mb-3 px-1">
                      <h3 className="text-sm font-semibold text-slate-400">
                        TODOS LOS MODELOS ({displayedModels.length})
                      </h3>
                    </div>
                  )}
                  <div className="space-y-1">
                    {displayedModels.map((model, index) => (
                      <ModelRow
                        key={model.id}
                        model={model}
                        isInstalling={model.id in installingModels}
                        installProgress={installingModels[model.id] || 0}
                        onInstall={() => handleInstall(model)}
                        onDelete={() => handleDelete(model)}
                        isSelected={index === selectedIndex}
                      />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Empty State */}
          {!loading && allLoaded && models.length === 0 && !allErrors && (
            <div className="fi-empty-state py-16">
              <div className="mb-3">
                {sourceFilter === 'installed' ? (
                  <Inbox className="w-12 h-12 text-slate-500" strokeWidth={1.5} />
                ) : (
                  <Search className="w-12 h-12 text-slate-500" strokeWidth={1.5} />
                )}
              </div>
              <h3 className="text-lg font-medium text-slate-400 mb-1">
                {sourceFilter === 'installed' ? 'No hay modelos instalados' : 'Sin resultados'}
              </h3>
              <p className="text-sm text-slate-500 text-center max-w-xs">
                {sourceFilter === 'installed'
                  ? 'Explora el catálogo para instalar modelos.'
                  : searchQuery
                  ? `No hay modelos que coincidan con "${searchQuery}".`
                  : 'Intenta con otros filtros.'}
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex-shrink-0 px-4 py-3 fi-border-top bg-slate-900/95">
          <div className="flex items-center justify-between fi-text-xs-muted">
            <div className="fi-flex-gap-lg">
              <span className="fi-flex-gap-sm">
                <Keyboard className="w-3.5 h-3.5" />
                <span>↑↓ navegar</span>
              </span>
              <span>Enter instalar</span>
              <span>Esc cerrar</span>
            </div>
            <span>/ para buscar</span>
          </div>
        </div>
      </div>
    </>
  );
}

export default ModelCatalogDrawer;
