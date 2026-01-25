/**
 * ModelCatalogDrawer Types
 */

import type { LucideIcon } from 'lucide-react';
import type { CatalogModel, CatalogSource, SourcesStatus, InstallProgress } from '@/lib/api/catalog';

export interface ModelCatalogDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onModelInstalled?: () => void;
}

export type SourceFilter = CatalogSource | 'all' | 'installed';

export type SourceLoadingState = 'idle' | 'loading' | 'loaded' | 'error';

export interface SourceState {
  status: SourceLoadingState;
  models: CatalogModel[];
  error?: string;
}

export interface FilterTab {
  key: SourceFilter;
  label: string;
  /** Lucide icon for general tabs, or 'provider' to use ProviderLogo with key as source */
  icon: LucideIcon | 'provider';
  count?: number;
}

export interface ModelRowProps {
  model: CatalogModel;
  isInstalling: boolean;
  installProgress: number;
  onInstall: () => void;
  onDelete: () => void;
  featured?: boolean;
  isSelected?: boolean;
}

// Re-export for convenience
export type { CatalogModel, CatalogSource, SourcesStatus, InstallProgress };
