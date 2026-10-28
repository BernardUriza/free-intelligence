import * as react from 'react';
import { f as AdminSheetProps } from '../controls-B6pgIbiJ.js';
import 'lucide-react';

type LLMProvider = 'openai' | 'anthropic' | 'azure' | 'ollama';
type CostTier = 'low' | 'medium' | 'high';
interface LLMModel {
    id: string;
    label: string;
    provider: LLMProvider;
    cost_tier: CostTier;
    max_tokens: number;
    context_window: number;
    is_active: boolean;
    description?: string | null;
    size_bytes?: number | null;
    ram_required_gb?: number | null;
    created_at: string;
    updated_at: string;
}
interface LLMModelCreate {
    id: string;
    label: string;
    provider: LLMProvider;
    cost_tier?: CostTier;
    max_tokens?: number;
    context_window?: number;
    is_active?: boolean;
    description?: string | null;
    size_bytes?: number | null;
    ram_required_gb?: number | null;
}
type LLMModelUpdate = Partial<Omit<LLMModelCreate, 'id'>>;
interface LLMModelFilter {
    includeInactive: boolean;
    provider?: LLMProvider;
}
interface ModelTestResult {
    success: boolean;
    model_id: string;
    prompt: string;
    response: string;
    error?: string | null;
}
type CatalogSource = 'gpt4all' | 'huggingface' | 'ollama';
type QuantizationType = 'Q4_0' | 'Q4_K_M' | 'Q5_K_M' | 'Q8_0' | 'F16' | 'unknown';
interface CatalogModel {
    id: string;
    name: string;
    filename: string;
    source: CatalogSource;
    source_url?: string;
    repo_id?: string;
    size_bytes: number;
    ram_required_gb?: number;
    parameters?: string;
    quantization: QuantizationType;
    context_length?: number;
    description?: string;
    license?: string;
    tags: string[];
    is_installed: boolean;
    installed_at?: string;
}
interface CatalogQuery {
    source: CatalogSource;
    query?: string;
    maxSizeGb?: number;
    signal?: AbortSignal;
}
interface InstallProgress {
    model_id: string;
    status: 'downloading' | 'extracting' | 'registering' | 'completed' | 'error';
    progress_percent: number;
    downloaded_bytes: number;
    total_bytes: number;
    message?: string;
    error?: string;
}
interface InstallOptions {
    onProgress: (progress: InstallProgress) => void;
    signal?: AbortSignal;
}
interface MemoryInfo {
    total_gb: number;
    available_gb: number;
    used_gb: number;
    percent_used: number;
}
interface SystemResources {
    memory: MemoryInfo;
    cpu_percent: number;
    cpu_count: number;
    platform: string;
    timestamp: string;
}
interface RunningModel {
    name: string;
    model_id: string;
    size_bytes: number;
    size_gb: number;
    vram_bytes: number | null;
    vram_gb: number | null;
    processor: 'cpu' | 'gpu' | 'partial';
    until: string | null;
}
interface RunningModelsResponse {
    models: RunningModel[];
    total_loaded_gb: number;
    ollama_available: boolean;
}
interface ModelCatalogStore {
    listModels(filter: LLMModelFilter): Promise<LLMModel[]>;
    createModel(request: LLMModelCreate): Promise<LLMModel>;
    updateModel(modelId: string, request: LLMModelUpdate): Promise<LLMModel>;
    deactivateModel(modelId: string): Promise<void>;
    testModel(modelId: string): Promise<ModelTestResult>;
    listCatalog(query: CatalogQuery): Promise<CatalogModel[]>;
    installCatalogModel(modelId: string, options: InstallOptions): Promise<void>;
    removeCatalogModel(modelId: string): Promise<void>;
    getSystemResources(): Promise<SystemResources>;
    listRunningModels(): Promise<RunningModelsResponse>;
    unloadRunningModel(modelName: string): Promise<void>;
}
type ModelCatalogConfirm = (message: string) => Promise<boolean>;
type ModelCatalogNotify = (kind: 'success' | 'error', message: string) => void;
declare const defaultModelCatalogConfirm: ModelCatalogConfirm;

declare const PROVIDER_INFO: Record<LLMProvider, {
    label: string;
}>;
declare const COST_TIER_INFO: Record<CostTier, {
    label: string;
    symbol: string;
}>;
declare const SOURCE_INFO: Record<CatalogSource, {
    label: string;
}>;
declare const QUANT_INFO: Record<QuantizationType, {
    label: string;
    quality: string;
}>;
declare const CATALOG_SOURCES: readonly CatalogSource[];
declare const FEATURED_MODEL_IDS: readonly string[];
declare const CATALOG_SIZE_OPTIONS: readonly {
    value: string;
    label: string;
}[];
declare function isLocalProvider(provider: LLMProvider): boolean;
declare function formatBytes(bytes: number): string;
declare function formatCount(n: number): string;
declare function formatTimeUntil(iso: string | null, now?: Date): string;
declare function usageLevel(percent: number): 'ok' | 'warn' | 'danger' | 'critical';
/** The registry entry an installed catalog model becomes (always a local, low-cost Ollama model). */
declare function catalogModelToCreate(model: CatalogModel): LLMModelCreate;

type ProviderOrSource = LLMProvider | CatalogSource | (string & {});
interface ProviderLogoProps {
    provider: ProviderOrSource;
    size?: number;
    className?: string;
}
declare function ProviderLogo({ provider, size, className }: ProviderLogoProps): react.JSX.Element;
/** The logo inside a tinted box; the tint follows the provider via `data-provider`. */
declare function ProviderLogoBox({ provider, size, className }: ProviderLogoProps): react.JSX.Element;

interface LLMModelCardProps {
    model: LLMModel;
    selected?: boolean;
    onSelect?: () => void;
    onEdit: () => void;
    onDeactivate: () => void;
    onToggleActive: () => void;
    /** Omit to hide the test action. It is offered only on active models. */
    onTest?: () => void;
    locale?: string;
}
declare function LLMModelCard({ model, selected, onSelect, onEdit, onDeactivate, onToggleActive, onTest, locale, }: LLMModelCardProps): react.JSX.Element;

interface LLMModelGridProps {
    models: readonly LLMModel[];
    loading: boolean;
    error: string | null;
    selectedId?: string | null;
    onSelect?: (modelId: string) => void;
    onEdit: (model: LLMModel) => void;
    onDeactivate: (model: LLMModel) => void;
    onToggleActive: (model: LLMModel) => void;
    onTest?: (model: LLMModel) => void;
    onRetry: () => void;
    onCreateFirst?: () => void;
    locale?: string;
}
declare function LLMModelGrid({ models, loading, error, selectedId, onSelect, onEdit, onDeactivate, onToggleActive, onTest, onRetry, onCreateFirst, locale, }: LLMModelGridProps): react.JSX.Element;

interface LLMModelFilterBarProps {
    provider: LLMProvider | '';
    onProviderChange: (provider: LLMProvider | '') => void;
    includeInactive: boolean;
    onIncludeInactiveChange: (includeInactive: boolean) => void;
}
declare function LLMModelFilterBar({ provider, onProviderChange, includeInactive, onIncludeInactiveChange, }: LLMModelFilterBarProps): react.JSX.Element;

interface LLMModelFormSheetProps {
    /** Present = edit that model; absent = create a new one. */
    model?: LLMModel;
    store: Pick<ModelCatalogStore, 'createModel' | 'updateModel'>;
    onClose: () => void;
    onSaved: (model: LLMModel) => void;
}
declare function sanitizeModelId(value: string): string;
declare function LLMModelFormSheet({ model, store, onClose, onSaved }: LLMModelFormSheetProps): react.JSX.Element;

interface ModelTestStage {
    title: string;
    text: string;
    /** Milliseconds after the test starts at which this stage is shown. */
    delay: number;
}
declare function modelTestStages(model: LLMModel): ModelTestStage[];
interface ModelTestState {
    model: LLMModel | null;
    running: boolean;
    stage: ModelTestStage | null;
    result: ModelTestResult | null;
    error: string | null;
    run: (model: LLMModel) => Promise<void>;
    close: () => void;
}
declare function useModelTest(store: Pick<ModelCatalogStore, 'testModel'>): ModelTestState;

type ModelTestSheetProps = Pick<ModelTestState, 'model' | 'running' | 'stage' | 'result' | 'error' | 'close'>;
declare function ModelTestSheet({ model, running, stage, result, error, close }: ModelTestSheetProps): react.JSX.Element | null;

interface UseSystemResourcesOptions {
    /** 0 disables polling. */
    pollIntervalMs?: number;
    notify?: ModelCatalogNotify;
}
interface SystemResourcesState {
    resources: SystemResources | null;
    running: RunningModelsResponse | null;
    loading: boolean;
    error: string | null;
    refresh: () => Promise<void>;
    unload: (modelName: string) => Promise<void>;
    unloading: string | null;
}
declare function useSystemResources(store: Pick<ModelCatalogStore, 'getSystemResources' | 'listRunningModels' | 'unloadRunningModel'>, { pollIntervalMs, notify }?: UseSystemResourcesOptions): SystemResourcesState;

type SystemResourcesPanelProps = Pick<SystemResourcesState, 'resources' | 'running' | 'loading' | 'error' | 'refresh' | 'unload' | 'unloading'>;
declare function SystemResourcesPanel({ resources, running, loading, error, refresh, unload, unloading }: SystemResourcesPanelProps): react.JSX.Element;

interface ModelCatalogDrawerProps {
    open: boolean;
    onClose: () => void;
    store: Pick<ModelCatalogStore, 'listCatalog' | 'installCatalogModel' | 'removeCatalogModel' | 'createModel'>;
    onModelsChanged?: () => void;
    confirm?: ModelCatalogConfirm;
    notify?: ModelCatalogNotify;
    /** Sources whose installed models can be deleted from disk. aurity's backend only removes from Ollama. */
    removableSources?: readonly CatalogSource[];
}
declare function ModelCatalogDrawer({ open, onClose, store, onModelsChanged, confirm, notify, removableSources, }: ModelCatalogDrawerProps): react.JSX.Element | null;
interface CatalogModelRowProps {
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
declare function CatalogModelRow({ model, progress, error, featured, selected, navigable, removable, onInstall, onRemove, }: CatalogModelRowProps): react.JSX.Element;

type ModelSheetProps = Omit<AdminSheetProps, 'className'>;
declare function ModelSheet(props: ModelSheetProps): react.JSX.Element;

interface UseLLMModelsOptions {
    confirm?: ModelCatalogConfirm;
    notify?: ModelCatalogNotify;
    deactivateConfirmMessage?: (model: LLMModel) => string;
}
interface LLMModelCollection {
    models: LLMModel[];
    loading: boolean;
    error: string | null;
    reload: () => Promise<void>;
    selectedId: string | null;
    setSelectedId: (modelId: string | null) => void;
    includeInactive: boolean;
    setIncludeInactive: (value: boolean) => void;
    provider: LLMProvider | '';
    setProvider: (value: LLMProvider | '') => void;
    /** Insert or replace by id (after a create or an edit). */
    upsert: (model: LLMModel) => void;
    /** Confirms, then soft-deletes through `store.deactivateModel`. Resolves true only if it happened. */
    deactivate: (model: LLMModel) => Promise<boolean>;
    toggleActive: (model: LLMModel) => Promise<void>;
    actionError: string | null;
    clearActionError: () => void;
}
declare const defaultDeactivateMessage: (model: LLMModel) => string;
declare function useLLMModels(store: Pick<ModelCatalogStore, 'listModels' | 'updateModel' | 'deactivateModel'>, { confirm, notify, deactivateConfirmMessage, }?: UseLLMModelsOptions): LLMModelCollection;

type CatalogFilter = CatalogSource | 'all' | 'installed';
type CatalogSourceStatus = 'idle' | 'loading' | 'loaded' | 'error';
interface CatalogSourceState {
    status: CatalogSourceStatus;
    models: CatalogModel[];
    error?: string;
}
interface UseModelCatalogOptions {
    /** The catalog loads when this turns true and aborts in-flight listings when it turns false. */
    open: boolean;
    /** Called after an install, removal or sync changed what the registry holds. */
    onModelsChanged?: () => void;
    confirm?: ModelCatalogConfirm;
    notify?: ModelCatalogNotify;
    removeConfirmMessage?: (model: CatalogModel) => string;
}
declare const defaultRemoveCatalogMessage: (model: CatalogModel) => string;
declare function useModelCatalog(store: Pick<ModelCatalogStore, 'listCatalog' | 'installCatalogModel' | 'removeCatalogModel' | 'createModel'>, { open, onModelsChanged, confirm, notify, removeConfirmMessage, }: UseModelCatalogOptions): {
    sourceStates: Record<CatalogSource, CatalogSourceState>;
    filter: CatalogFilter;
    setFilter: react.Dispatch<react.SetStateAction<CatalogFilter>>;
    searchQuery: string;
    setSearchQuery: react.Dispatch<react.SetStateAction<string>>;
    maxSizeGb: number | undefined;
    setMaxSizeGb: react.Dispatch<react.SetStateAction<number | undefined>>;
    installing: Record<string, number>;
    installErrors: Record<string, string>;
    syncing: boolean;
    allModels: CatalogModel[];
    models: CatalogModel[];
    featuredModels: CatalogModel[];
    displayedModels: CatalogModel[];
    installedCount: number;
    loading: boolean;
    allLoaded: boolean;
    allErrors: boolean;
    reload: () => void;
    install: (model: CatalogModel) => Promise<void>;
    remove: (model: CatalogModel) => Promise<boolean>;
    syncInstalled: () => Promise<void>;
};
type ModelCatalogState = ReturnType<typeof useModelCatalog>;

interface UseCatalogKeyboardNavigationOptions {
    open: boolean;
    models: readonly CatalogModel[];
    installing: Record<string, number>;
    onInstall: (model: CatalogModel) => void;
}
/** `/` focuses search, arrows move the selection, Enter installs the selected row. */
declare function useCatalogKeyboardNavigation({ open, models, installing, onInstall }: UseCatalogKeyboardNavigationOptions): {
    selectedIndex: number;
    listRef: react.RefObject<HTMLDivElement | null>;
    searchRef: react.RefObject<HTMLInputElement | null>;
};

declare const FI_MODEL_CATALOG_ROOT_CLASS = "fi-model-catalog";
/** Inject the idempotent model-catalog stylesheet (no-op on the server / if already present). */
declare function ensureModelCatalogStyle(): void;
declare function useModelCatalogStyle(): void;

export { CATALOG_SIZE_OPTIONS, CATALOG_SOURCES, COST_TIER_INFO, type CatalogFilter, type CatalogModel, CatalogModelRow, type CatalogModelRowProps, type CatalogQuery, type CatalogSource, type CatalogSourceState, type CatalogSourceStatus, type CostTier, FEATURED_MODEL_IDS, FI_MODEL_CATALOG_ROOT_CLASS, type InstallOptions, type InstallProgress, type LLMModel, LLMModelCard, type LLMModelCardProps, type LLMModelCollection, type LLMModelCreate, type LLMModelFilter, LLMModelFilterBar, type LLMModelFilterBarProps, LLMModelFormSheet, type LLMModelFormSheetProps, LLMModelGrid, type LLMModelGridProps, type LLMModelUpdate, type LLMProvider, type MemoryInfo, type ModelCatalogConfirm, ModelCatalogDrawer, type ModelCatalogDrawerProps, type ModelCatalogNotify, type ModelCatalogState, type ModelCatalogStore, ModelSheet, type ModelSheetProps, type ModelTestResult, ModelTestSheet, type ModelTestSheetProps, type ModelTestStage, type ModelTestState, PROVIDER_INFO, ProviderLogo, ProviderLogoBox, type ProviderLogoProps, type ProviderOrSource, QUANT_INFO, type QuantizationType, type RunningModel, type RunningModelsResponse, SOURCE_INFO, type SystemResources, SystemResourcesPanel, type SystemResourcesPanelProps, type SystemResourcesState, type UseCatalogKeyboardNavigationOptions, type UseLLMModelsOptions, type UseModelCatalogOptions, type UseSystemResourcesOptions, catalogModelToCreate, defaultDeactivateMessage, defaultModelCatalogConfirm, defaultRemoveCatalogMessage, ensureModelCatalogStyle, formatBytes, formatCount, formatTimeUntil, isLocalProvider, modelTestStages, sanitizeModelId, usageLevel, useCatalogKeyboardNavigation, useLLMModels, useModelCatalog, useModelCatalogStyle, useModelTest, useSystemResources };
