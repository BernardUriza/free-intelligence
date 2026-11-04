// fi-glass · model-catalog: the LLM model registry, the online/offline catalog with downloads, and host resources.
// Also importable via `fi-glass/model-catalog`; extracted from aurity's /admin/models. All I/O goes through a ModelCatalogStore.
export type {
  LLMProvider,
  CostTier,
  LLMModel,
  LLMModelCreate,
  LLMModelUpdate,
  LLMModelFilter,
  ModelTestResult,
  CatalogSource,
  QuantizationType,
  CatalogModel,
  CatalogQuery,
  InstallProgress,
  InstallOptions,
  MemoryInfo,
  SystemResources,
  RunningModel,
  RunningModelsResponse,
  ModelCatalogStore,
  ModelCatalogConfirm,
  ModelCatalogNotify,
} from './types';
export { defaultModelCatalogConfirm } from './types';

export {
  PROVIDER_INFO,
  COST_TIER_INFO,
  SOURCE_INFO,
  QUANT_INFO,
  CATALOG_SOURCES,
  FEATURED_MODEL_IDS,
  CATALOG_SIZE_OPTIONS,
  isLocalProvider,
  formatBytes,
  formatCount,
  formatTimeUntil,
  usageLevel,
  catalogModelToCreate,
} from './format';

export { ProviderLogo, ProviderLogoBox, type ProviderLogoProps, type ProviderOrSource } from './ProviderLogo';
export { LLMModelCard, type LLMModelCardProps } from './LLMModelCard';
export { LLMModelGrid, type LLMModelGridProps } from './LLMModelGrid';
export { LLMModelFilterBar, type LLMModelFilterBarProps } from './LLMModelFilterBar';
export { LLMModelFormSheet, sanitizeModelId, type LLMModelFormSheetProps } from './LLMModelFormSheet';
export { ModelTestSheet, type ModelTestSheetProps } from './ModelTestSheet';
export { SystemResourcesPanel, type SystemResourcesPanelProps } from './SystemResourcesPanel';
export { ModelCatalogDrawer, CatalogModelRow, type ModelCatalogDrawerProps, type CatalogModelRowProps } from './ModelCatalogDrawer';
export { ModelSheet, type ModelSheetProps } from './ModelSheet';

export {
  useLLMModels,
  defaultDeactivateMessage,
  type LLMModelCollection,
  type UseLLMModelsOptions,
} from './useLLMModels';
export { useSystemResources, type SystemResourcesState, type UseSystemResourcesOptions } from './useSystemResources';
export { useModelTest, modelTestStages, type ModelTestState, type ModelTestStage } from './useModelTest';
export {
  useModelCatalog,
  defaultRemoveCatalogMessage,
  type ModelCatalogState,
  type UseModelCatalogOptions,
  type CatalogFilter,
  type CatalogSourceState,
  type CatalogSourceStatus,
} from './useModelCatalog';
export { useCatalogKeyboardNavigation, type UseCatalogKeyboardNavigationOptions } from './useCatalogKeyboardNavigation';
export { FI_MODEL_CATALOG_ROOT_CLASS, ensureModelCatalogStyle, useModelCatalogStyle } from './modelCatalogStyle';
