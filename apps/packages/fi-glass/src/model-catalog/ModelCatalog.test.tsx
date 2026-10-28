// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { LLMModelFilterBar } from './LLMModelFilterBar';
import { LLMModelFormSheet } from './LLMModelFormSheet';
import { LLMModelGrid } from './LLMModelGrid';
import { ModelCatalogDrawer } from './ModelCatalogDrawer';
import { ModelTestSheet } from './ModelTestSheet';
import { SystemResourcesPanel } from './SystemResourcesPanel';
import { catalogModelToCreate } from './format';
import { useLLMModels } from './useLLMModels';
import { useModelTest } from './useModelTest';
import { useSystemResources } from './useSystemResources';
import type { CatalogModel, CatalogQuery, InstallOptions, LLMModel, ModelCatalogStore } from './types';

const cloud: LLMModel = {
  id: 'gpt-4o-mini',
  label: 'GPT-4o Mini',
  provider: 'openai',
  cost_tier: 'medium',
  max_tokens: 4096,
  context_window: 128000,
  is_active: true,
  description: 'Balance',
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-02T00:00:00Z',
};
const local: LLMModel = { ...cloud, id: 'qwen3:1.7b', label: 'Qwen3 1.7B', provider: 'ollama', cost_tier: 'low', size_bytes: 1_400_000_000 };

const catalogModel = (over: Partial<CatalogModel>): CatalogModel => ({
  id: 'tinyllama',
  name: 'TinyLlama',
  filename: 'tinyllama.gguf',
  source: 'ollama',
  size_bytes: 600_000_000,
  quantization: 'Q4_0',
  tags: [],
  is_installed: false,
  ...over,
});
const tiny = catalogModel({});
const installedHf = catalogModel({ id: 'hf-phi', name: 'Phi HF', source: 'huggingface', is_installed: true });
const gptAll = catalogModel({ id: 'gpt4all-orca', name: 'Orca', source: 'gpt4all' });

function makeStore(overrides: Partial<ModelCatalogStore> = {}): ModelCatalogStore {
  return {
    listModels: vi.fn(async () => [cloud, local]),
    createModel: vi.fn(async (req) => ({ ...cloud, ...req }) as LLMModel),
    updateModel: vi.fn(async (id, req) => ({ ...(id === local.id ? local : cloud), ...req }) as LLMModel),
    deactivateModel: vi.fn(async () => {}),
    testModel: vi.fn(async (id) => ({ success: true, model_id: id, prompt: '¿Qué es la HTA?', response: 'Presión alta.' })),
    listCatalog: vi.fn(async ({ source }: CatalogQuery) => ({ ollama: [tiny], huggingface: [installedHf], gpt4all: [gptAll] })[source]),
    installCatalogModel: vi.fn(async () => {}),
    removeCatalogModel: vi.fn(async () => {}),
    getSystemResources: vi.fn(async () => ({
      memory: { total_gb: 16, available_gb: 6, used_gb: 10, percent_used: 62.5 },
      cpu_percent: 12,
      cpu_count: 8,
      platform: 'Darwin',
      timestamp: '2026-10-28T00:00:00Z',
    })),
    listRunningModels: vi.fn(async () => ({
      models: [
        { name: 'qwen3:1.7b', model_id: 'qwen3:1.7b', size_bytes: 1, size_gb: 1.4, vram_bytes: null, vram_gb: null, processor: 'gpu' as const, until: null },
      ],
      total_loaded_gb: 1.4,
      ollama_available: true,
    })),
    unloadRunningModel: vi.fn(async () => {}),
    ...overrides,
  };
}

function ModelsHarness({
  store,
  confirm,
  notify,
}: {
  store: ModelCatalogStore;
  confirm?: (m: string) => Promise<boolean>;
  notify?: (k: 'success' | 'error', m: string) => void;
}) {
  const c = useLLMModels(store, { confirm, notify });
  return (
    <>
      <LLMModelFilterBar
        provider={c.provider}
        onProviderChange={c.setProvider}
        includeInactive={c.includeInactive}
        onIncludeInactiveChange={c.setIncludeInactive}
      />
      {c.actionError ? <p data-testid="action-error">{c.actionError}</p> : null}
      <LLMModelGrid
        models={c.models}
        loading={c.loading}
        error={c.error}
        onEdit={vi.fn()}
        onDeactivate={(m) => void c.deactivate(m)}
        onToggleActive={(m) => void c.toggleActive(m)}
        onRetry={() => void c.reload()}
      />
    </>
  );
}

describe('the model registry', () => {
  it('lists through the store and filters local (offline) vs cloud and inactive models', async () => {
    const store = makeStore();
    render(<ModelsHarness store={store} />);
    expect(await screen.findByRole('article', { name: 'gpt-4o-mini' })).toBeTruthy();
    expect(store.listModels).toHaveBeenLastCalledWith({ includeInactive: false, provider: undefined });

    fireEvent.change(screen.getByLabelText('Proveedor'), { target: { value: 'ollama' } });
    await waitFor(() => expect(store.listModels).toHaveBeenLastCalledWith({ includeInactive: false, provider: 'ollama' }));

    fireEvent.click(screen.getByLabelText('Mostrar inactivos'));
    await waitFor(() => expect(store.listModels).toHaveBeenLastCalledWith({ includeInactive: true, provider: 'ollama' }));
  });

  it('shows RAM for a local model and the cost tier for a cloud one', async () => {
    render(<ModelsHarness store={makeStore()} />);
    const localCard = await screen.findByRole('article', { name: 'qwen3:1.7b' });
    expect(within(localCard).getByText('RAM')).toBeTruthy();
    expect(within(localCard).getByText('1.4 GB')).toBeTruthy();
    expect(within(screen.getByRole('article', { name: 'gpt-4o-mini' })).getByText('$$ Balance')).toBeTruthy();
  });

  it("surfaces the store's load error and retries", async () => {
    const listModels = vi.fn().mockRejectedValueOnce(new Error('Backend caído')).mockResolvedValue([cloud]);
    render(<ModelsHarness store={makeStore({ listModels })} />);
    expect(await screen.findByText('Backend caído')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByRole('article', { name: 'gpt-4o-mini' })).toBeTruthy();
  });

  it('deactivates only after the injected confirm says yes', async () => {
    const store = makeStore();
    const confirm = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    render(<ModelsHarness store={store} confirm={confirm} />);
    const card = await screen.findByRole('article', { name: 'gpt-4o-mini' });

    fireEvent.click(within(card).getByRole('button', { name: 'Eliminar modelo' }));
    await waitFor(() => expect(confirm).toHaveBeenCalledTimes(1));
    expect(store.deactivateModel).not.toHaveBeenCalled();

    fireEvent.click(within(card).getByRole('button', { name: 'Eliminar modelo' }));
    await waitFor(() => expect(store.deactivateModel).toHaveBeenCalledWith('gpt-4o-mini'));
    expect(confirm.mock.calls[1][0]).toContain('gpt-4o-mini');
    expect(await within(card).findByText('Inactivo')).toBeTruthy();
  });

  it('surfaces a failed deactivate inline and through notify', async () => {
    const notify = vi.fn();
    const store = makeStore({ deactivateModel: vi.fn(async () => Promise.reject(new Error('Sin permisos'))) });
    render(<ModelsHarness store={store} confirm={async () => true} notify={notify} />);
    const card = await screen.findByRole('article', { name: 'gpt-4o-mini' });
    fireEvent.click(within(card).getByRole('button', { name: 'Eliminar modelo' }));
    expect((await screen.findByTestId('action-error')).textContent).toBe('Sin permisos');
    expect(notify).toHaveBeenCalledWith('error', 'Sin permisos');
  });

  it('toggles active through store.updateModel', async () => {
    const store = makeStore();
    render(<ModelsHarness store={store} />);
    const card = await screen.findByRole('article', { name: 'gpt-4o-mini' });
    fireEvent.click(within(card).getByRole('button', { name: 'Desactivar modelo' }));
    await waitFor(() => expect(store.updateModel).toHaveBeenCalledWith('gpt-4o-mini', { is_active: false }));
  });
});

describe('LLMModelFormSheet', () => {
  it('creates with a sanitized id', async () => {
    const store = makeStore();
    const onSaved = vi.fn();
    const onClose = vi.fn();
    render(<LLMModelFormSheet store={store} onSaved={onSaved} onClose={onClose} />);
    fireEvent.change(screen.getByLabelText(/ID del modelo/), { target: { value: 'My Model' } });
    fireEvent.change(screen.getByLabelText(/Label/), { target: { value: 'Mi modelo' } });
    fireEvent.click(screen.getByRole('button', { name: 'Crear modelo' }));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(store.createModel).toHaveBeenCalledWith(expect.objectContaining({ id: 'my-model', label: 'Mi modelo', provider: 'openai' }));
    expect(onClose).toHaveBeenCalled();
  });

  it('edits without sending the id, and keeps the sheet open on a store error', async () => {
    const store = makeStore({ updateModel: vi.fn(async () => Promise.reject(new Error('Label duplicado'))) });
    const onClose = vi.fn();
    render(<LLMModelFormSheet model={cloud} store={store} onSaved={vi.fn()} onClose={onClose} />);
    expect(screen.queryByLabelText(/ID del modelo/)).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    expect(await screen.findByText('Label duplicado')).toBeTruthy();
    expect(vi.mocked(store.updateModel).mock.calls[0][1]).not.toHaveProperty('id');
    expect(onClose).not.toHaveBeenCalled();
  });

  it('does not call the store without a label', () => {
    const store = makeStore();
    render(<LLMModelFormSheet store={store} onSaved={vi.fn()} onClose={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(/ID del modelo/), { target: { value: 'x' } });
    fireEvent.click(screen.getByRole('button', { name: 'Crear modelo' }));
    expect(screen.getByText('El label es requerido')).toBeTruthy();
    expect(store.createModel).not.toHaveBeenCalled();
  });
});

describe('ModelCatalogDrawer', () => {
  it('loads every source through the store and filters installed / per source', async () => {
    const store = makeStore();
    render(<ModelCatalogDrawer open onClose={vi.fn()} store={store} />);
    expect(await screen.findByRole('listitem', { name: 'TinyLlama' })).toBeTruthy();
    expect(vi.mocked(store.listCatalog).mock.calls.map(([q]) => q.source).sort()).toEqual(['gpt4all', 'huggingface', 'ollama']);
    expect(screen.getByText('3 modelos · 1 instalados')).toBeTruthy();

    fireEvent.click(screen.getByRole('tab', { name: /Instalados/ }));
    await waitFor(() => expect(screen.queryByRole('listitem', { name: 'TinyLlama' })).toBeNull());
    expect(await screen.findByRole('listitem', { name: 'Phi HF' })).toBeTruthy();

    vi.mocked(store.listCatalog).mockClear();
    fireEvent.click(screen.getByRole('tab', { name: /Ollama/ }));
    await waitFor(() => expect(store.listCatalog).toHaveBeenCalledTimes(1));
    expect(vi.mocked(store.listCatalog).mock.calls[0][0]).toMatchObject({ source: 'ollama' });
    expect(await screen.findByRole('listitem', { name: 'TinyLlama' })).toBeTruthy();
    expect(screen.queryByRole('listitem', { name: 'Orca' })).toBeNull();
  });

  it('renders download progress, then registers the installed model', async () => {
    let options: InstallOptions | undefined;
    let finish: () => void = () => {};
    const installCatalogModel = vi.fn(
      (_id: string, opts: InstallOptions) =>
        new Promise<void>((resolve) => {
          options = opts;
          finish = resolve;
        }),
    );
    const store = makeStore({ installCatalogModel });
    const onModelsChanged = vi.fn();
    const notify = vi.fn();
    render(<ModelCatalogDrawer open onClose={vi.fn()} store={store} onModelsChanged={onModelsChanged} notify={notify} />);
    const row = await screen.findByRole('listitem', { name: 'TinyLlama' });
    fireEvent.click(within(row).getByRole('button', { name: 'Instalar TinyLlama' }));
    expect(installCatalogModel).toHaveBeenCalledWith('tinyllama', expect.objectContaining({ onProgress: expect.any(Function) }));

    act(() => {
      options!.onProgress({ model_id: 'tinyllama', status: 'downloading', progress_percent: 42, downloaded_bytes: 1, total_bytes: 2 });
    });
    expect(within(row).getByRole('progressbar').getAttribute('aria-valuenow')).toBe('42');
    expect(within(row).getByText('Instalando... 42%')).toBeTruthy();

    await act(async () => finish());
    await waitFor(() => expect(store.createModel).toHaveBeenCalledWith(catalogModelToCreate(tiny)));
    expect(onModelsChanged).toHaveBeenCalled();
    expect(notify).toHaveBeenCalledWith('success', 'TinyLlama instalado y registrado');
    expect(within(row).getByText('Instalado')).toBeTruthy();
    expect(within(row).queryByRole('progressbar')).toBeNull();
  });

  it('surfaces a failed download in the row and through notify', async () => {
    const notify = vi.fn();
    const store = makeStore({ installCatalogModel: vi.fn(async () => Promise.reject(new Error('Timeout: sin actividad por 30s'))) });
    render(<ModelCatalogDrawer open onClose={vi.fn()} store={store} notify={notify} />);
    const row = await screen.findByRole('listitem', { name: 'TinyLlama' });
    fireEvent.click(within(row).getByRole('button', { name: 'Instalar TinyLlama' }));
    expect(await within(row).findByText('Timeout: sin actividad por 30s')).toBeTruthy();
    expect(notify).toHaveBeenCalledWith('error', 'TinyLlama: Timeout: sin actividad por 30s');
    expect(store.createModel).not.toHaveBeenCalled();
    expect(within(row).getByRole('button', { name: 'Instalar TinyLlama' })).toBeTruthy();
  });

  it('removes an installed model only after the injected confirm, and only from removable sources', async () => {
    const installedOllama = catalogModel({ id: 'llama-local', name: 'Llama Local', is_installed: true });
    const store = makeStore({
      listCatalog: vi.fn(async ({ source }) => (source === 'ollama' ? [installedOllama] : source === 'huggingface' ? [installedHf] : [])),
    });
    const confirm = vi.fn(async () => true);
    render(<ModelCatalogDrawer open onClose={vi.fn()} store={store} confirm={confirm} />);
    const row = await screen.findByRole('listitem', { name: 'Llama Local' });
    expect(within(await screen.findByRole('listitem', { name: 'Phi HF' })).queryByRole('button', { name: /Eliminar/ })).toBeNull();
    fireEvent.click(within(row).getByRole('button', { name: 'Eliminar Llama Local' }));
    await waitFor(() => expect(store.removeCatalogModel).toHaveBeenCalledWith('llama-local'));
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('Llama Local'));
    expect(await within(row).findByRole('button', { name: 'Instalar Llama Local' })).toBeTruthy();
  });

  it('shows a retry when every source fails', async () => {
    const store = makeStore({ listCatalog: vi.fn(async () => Promise.reject(new Error('offline'))) });
    render(<ModelCatalogDrawer open onClose={vi.fn()} store={store} />);
    expect(await screen.findByText('Error al cargar todas las fuentes')).toBeTruthy();
    vi.mocked(store.listCatalog).mockImplementation(async ({ source }) => (source === 'ollama' ? [tiny] : []));
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByRole('listitem', { name: 'TinyLlama' })).toBeTruthy();
  });

  it('installs the selected row from the keyboard only while the search or the list owns the key', async () => {
    const store = makeStore();
    render(<ModelCatalogDrawer open onClose={vi.fn()} store={store} />);
    await screen.findByRole('listitem', { name: 'TinyLlama' });
    const search = screen.getByRole('searchbox', { name: 'Buscar modelos' });
    fireEvent.keyDown(search, { key: 'ArrowDown' });
    expect(screen.getByRole('listitem', { name: 'TinyLlama' }).getAttribute('data-selected')).toBe('true');

    const reload = screen.getByRole('button', { name: 'Recargar catálogo' });
    fireEvent.keyDown(reload, { key: 'Enter' });
    fireEvent.keyDown(screen.getByRole('combobox', { name: 'Tamaño máximo' }), { key: 'ArrowDown' });
    expect(store.installCatalogModel).not.toHaveBeenCalled();
    expect(screen.getByRole('listitem', { name: 'TinyLlama' }).getAttribute('data-selected')).toBe('true');

    fireEvent.keyDown(search, { key: 'Enter' });
    expect(store.installCatalogModel).toHaveBeenCalledWith('tinyllama', expect.anything());
  });

  it('renders nothing and lists nothing while closed', () => {
    const store = makeStore();
    const { container } = render(<ModelCatalogDrawer open={false} onClose={vi.fn()} store={store} />);
    expect(container.innerHTML).toBe('');
    expect(store.listCatalog).not.toHaveBeenCalled();
  });
});

function TestHarness({ store }: { store: ModelCatalogStore }) {
  const t = useModelTest(store);
  return (
    <>
      <button type="button" onClick={() => void t.run(cloud)}>
        probar
      </button>
      <ModelTestSheet {...t} />
    </>
  );
}

describe('model test', () => {
  it('shows the prompt and the response as text', async () => {
    const store = makeStore({
      testModel: vi.fn(async () => ({ success: true, model_id: 'gpt-4o-mini', prompt: 'Hola', response: '<b>negritas</b>' })),
    });
    render(<TestHarness store={store} />);
    fireEvent.click(screen.getByText('probar'));
    expect(await screen.findByText('<b>negritas</b>')).toBeTruthy();
    expect(screen.getByText('Hola')).toBeTruthy();
    expect(store.testModel).toHaveBeenCalledWith('gpt-4o-mini');
  });

  it("shows the store's error", async () => {
    render(<TestHarness store={makeStore({ testModel: vi.fn(async () => Promise.reject(new Error('Modelo no responde'))) })} />);
    fireEvent.click(screen.getByText('probar'));
    expect(await screen.findByText('Modelo no responde')).toBeTruthy();
    expect(screen.getByText('Error al probar gpt-4o-mini')).toBeTruthy();
  });
});

function ResourcesHarness({ store }: { store: ModelCatalogStore }) {
  return <SystemResourcesPanel {...useSystemResources(store, { pollIntervalMs: 0 })} />;
}

describe('SystemResourcesPanel', () => {
  it('renders RAM and the running models, and unloads through the store', async () => {
    const store = makeStore();
    render(<ResourcesHarness store={store} />);
    expect(await screen.findByText('10.0GB / 16.0GB')).toBeTruthy();
    expect(screen.getByRole('meter').getAttribute('aria-valuenow')).toBe('63');
    fireEvent.click(screen.getByRole('button', { name: 'Descargar qwen3:1.7b de memoria' }));
    await waitFor(() => expect(store.unloadRunningModel).toHaveBeenCalledWith('qwen3:1.7b'));
    await waitFor(() => expect(store.getSystemResources).toHaveBeenCalledTimes(2));
  });

  it("surfaces the store's error", async () => {
    render(<ResourcesHarness store={makeStore({ getSystemResources: vi.fn(async () => Promise.reject(new Error('Sin acceso al host'))) })} />);
    expect(await screen.findByText('Sin acceso al host')).toBeTruthy();
  });
});
