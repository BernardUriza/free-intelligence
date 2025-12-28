/**
 * ModelCatalogDrawer Module
 *
 * A slide-over drawer for browsing and installing models from
 * GPT4All, HuggingFace, and Ollama catalogs.
 *
 * Modular structure:
 * - types.ts: TypeScript interfaces
 * - constants.ts: Configuration and static data
 * - hooks/: useModelCatalog, useKeyboardNavigation
 * - components/: ModelRow, ModelRowSkeleton, SourceLoadingStatus, FilterTabs
 */

export { ModelCatalogDrawer, default } from './ModelCatalogDrawer';
export type { ModelCatalogDrawerProps } from './types';
