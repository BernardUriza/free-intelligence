// @vitest-environment jsdom
import { describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { PersonaCreateModal } from './PersonaCreateModal';
import { PersonaEditor } from './PersonaEditor';
import { PersonaCard } from './PersonaCard';
import { usePersonaCollection } from './usePersonaCollection';
import type { Persona, PersonaStore } from './types';

const persona: Persona = {
  id: 'soap_editor',
  name: 'SOAP Editor',
  description: 'Edita notas SOAP clínicas.',
  system_prompt: 'Eres un editor de notas SOAP muy preciso.',
  model: 'gpt-4o',
  voice: 'nova',
  temperature: 0.3,
  max_tokens: 1024,
  examples: [],
  usage_stats: { total_invocations: 12, avg_latency_ms: 300, avg_cost_usd: 0.002 },
  version: 3,
  last_updated: '2026-10-01T00:00:00Z',
  updated_by: 'bernard',
};

const models = [
  { value: 'gpt-4o', label: 'GPT-4o' },
  { value: 'claude-opus', label: 'Claude Opus', group: 'Anthropic' },
];
const voices = [{ value: 'nova', label: 'Nova' }];

function makeStore(overrides: Partial<PersonaStore> = {}): PersonaStore {
  return {
    list: vi.fn(async () => [persona]),
    get: vi.fn(async () => ({ ...persona })),
    create: vi.fn(async (req) => ({ ...persona, ...req, voice: req.voice ?? null, examples: req.examples ?? [] }) as Persona),
    update: vi.fn(async (_id, req) => ({ ...persona, ...req }) as Persona),
    remove: vi.fn(async () => {}),
    test: vi.fn(async () => ({ output: 'hola', latency_ms: 120, tokens_used: 9, cost_usd: 0.0001 })),
    ...overrides,
  };
}

function fillCreate() {
  fireEvent.change(screen.getByLabelText(/Nombre/), { target: { value: 'Asistente Nutrición' } });
  fireEvent.change(screen.getByLabelText(/Descripción/), { target: { value: 'Orienta sobre alimentación.' } });
  fireEvent.change(screen.getByLabelText(/System Prompt/), {
    target: { value: 'Eres un asistente especializado en nutrición.' },
  });
}

describe('PersonaCreateModal', () => {
  it('maps the form into store.create and reports the created persona', async () => {
    const store = makeStore();
    const onCreated = vi.fn();
    const onOpenChange = vi.fn();
    render(
      <PersonaCreateModal
        open
        onOpenChange={onOpenChange}
        store={store}
        onCreated={onCreated}
        modelOptions={models}
        voiceOptions={voices}
        initialValues={{ model: 'claude-opus' }}
      />,
    );
    fillCreate();
    expect((screen.getByLabelText(/ID único/) as HTMLInputElement).value).toBe('asistente_nutricion');
    fireEvent.click(screen.getByRole('button', { name: /Crear persona/ }));
    await waitFor(() => expect(onCreated).toHaveBeenCalledTimes(1));
    expect(store.create).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'asistente_nutricion',
        name: 'Asistente Nutrición',
        model: 'claude-opus',
        voice: 'nova',
        temperature: 0.7,
        max_tokens: 2048,
        examples: [],
      }),
    );
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("shows the store's error message and stays open", async () => {
    const store = makeStore({ create: vi.fn(async () => Promise.reject(new Error('Ya existe una persona con ese ID'))) });
    const onOpenChange = vi.fn();
    render(
      <PersonaCreateModal open onOpenChange={onOpenChange} store={store} onCreated={vi.fn()} modelOptions={models} />,
    );
    fillCreate();
    fireEvent.click(screen.getByRole('button', { name: /Crear persona/ }));
    expect(await screen.findByText('Ya existe una persona con ese ID')).toBeTruthy();
    expect(onOpenChange).not.toHaveBeenCalled();
  });

  it('does not call the store while the form is invalid', () => {
    const store = makeStore();
    render(<PersonaCreateModal open onOpenChange={vi.fn()} store={store} onCreated={vi.fn()} modelOptions={models} />);
    fireEvent.click(screen.getByRole('button', { name: /Crear persona/ }));
    expect(store.create).not.toHaveBeenCalled();
    expect(screen.getByText('El nombre es requerido')).toBeTruthy();
  });

  it('hides fields the engine ignores and omits them from the request', async () => {
    const store = makeStore();
    render(
      <PersonaCreateModal
        open
        onOpenChange={vi.fn()}
        store={store}
        onCreated={vi.fn()}
        modelOptions={models}
        voiceOptions={voices}
        hiddenFields={['voice', 'temperature', 'max_tokens']}
      />,
    );
    expect(screen.queryByLabelText(/Voz/)).toBeNull();
    expect(screen.queryByLabelText(/Temperatura/)).toBeNull();
    expect(screen.queryByLabelText(/Max tokens/)).toBeNull();
    fillCreate();
    fireEvent.click(screen.getByRole('button', { name: /Crear persona/ }));
    await waitFor(() => expect(store.create).toHaveBeenCalled());
    const request = vi.mocked(store.create).mock.calls[0][0];
    expect(request).not.toHaveProperty('voice');
    expect(request).not.toHaveProperty('max_tokens');
  });

  it('renders the consumer options, grouped, plus an extra-fields slot that can block submit', () => {
    const store = makeStore();
    render(
      <PersonaCreateModal
        open
        onOpenChange={vi.fn()}
        store={store}
        onCreated={vi.fn()}
        modelOptions={models}
        renderExtraFields={() => <p>Elige un slot</p>}
        validateExtra={() => 'Falta el slot'}
      />,
    );
    const select = screen.getByLabelText(/Modelo/) as HTMLSelectElement;
    expect([...select.options].map((o) => o.textContent)).toEqual(['GPT-4o', 'Claude Opus']);
    expect(select.querySelector('optgroup')?.getAttribute('label')).toBe('Anthropic');
    expect(screen.getByText('Elige un slot')).toBeTruthy();
    fillCreate();
    fireEvent.click(screen.getByRole('button', { name: /Crear persona/ }));
    expect(screen.getByText('Falta el slot')).toBeTruthy();
    expect(store.create).not.toHaveBeenCalled();
  });
});

describe('PersonaEditor', () => {
  const renderEditor = (store: PersonaStore, extra: Partial<Parameters<typeof PersonaEditor>[0]> = {}) =>
    render(
      <PersonaEditor
        personaId="soap_editor"
        open
        onClose={vi.fn()}
        onSaved={vi.fn()}
        store={store}
        modelOptions={models}
        voiceOptions={voices}
        {...extra}
      />,
    );

  it('loads through store.get and saves edits through store.update', async () => {
    const store = makeStore();
    const onSaved = vi.fn();
    renderEditor(store, { onSaved });
    const name = (await screen.findByLabelText(/Nombre/)) as HTMLInputElement;
    expect(store.get).toHaveBeenCalledWith('soap_editor');
    fireEvent.change(name, { target: { value: 'SOAP Pro' } });
    fireEvent.click(screen.getByRole('button', { name: /Guardar cambios/ }));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(store.update).toHaveBeenCalledWith('soap_editor', expect.objectContaining({ name: 'SOAP Pro', model: 'gpt-4o' }));
  });

  it('removes only after the injected confirm says yes', async () => {
    const store = makeStore();
    const onDeleted = vi.fn();
    const confirm = vi.fn(async () => false);
    const { rerender } = renderEditor(store, { onDeleted, confirm });
    fireEvent.click(await screen.findByRole('button', { name: /Eliminar/ }));
    await waitFor(() => expect(confirm).toHaveBeenCalledWith(expect.stringContaining('SOAP Editor')));
    expect(store.remove).not.toHaveBeenCalled();

    const yes = vi.fn(async () => true);
    rerender(
      <PersonaEditor
        personaId="soap_editor"
        open
        onClose={vi.fn()}
        onSaved={vi.fn()}
        store={store}
        modelOptions={models}
        onDeleted={onDeleted}
        confirm={yes}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /Eliminar/ }));
    await waitFor(() => expect(onDeleted).toHaveBeenCalledWith('soap_editor'));
    expect(store.remove).toHaveBeenCalledWith('soap_editor');
  });

  it('runs a test through store.test and renders the output', async () => {
    const store = makeStore();
    renderEditor(store);
    fireEvent.click(await screen.findByRole('tab', { name: /Probar/ }));
    fireEvent.change(screen.getByLabelText(/Input de prueba/), { target: { value: 'hola' } });
    fireEvent.click(screen.getByRole('button', { name: /Probar persona/ }));
    expect((await screen.findByTestId('persona-test-output')).textContent).toBe('hola');
    expect(store.test).toHaveBeenCalledWith('soap_editor', 'hola');
  });

  it('hides the examples tab and the hidden fields', async () => {
    renderEditor(makeStore(), { hiddenFields: ['examples', 'voice'] });
    await screen.findByLabelText(/Nombre/);
    expect(screen.queryByRole('tab', { name: /Examples/ })).toBeNull();
    expect(screen.queryByLabelText(/Voz/)).toBeNull();
    expect(screen.queryByRole('button', { name: /Eliminar/ })).toBeNull();
  });
});

describe('PersonaCard and usePersonaCollection', () => {
  it('only offers delete when the consumer passes onDelete', () => {
    const { rerender } = render(<PersonaCard persona={persona} onEdit={vi.fn()} />);
    expect(screen.queryByRole('button', { name: 'Eliminar persona' })).toBeNull();
    const onDelete = vi.fn();
    rerender(<PersonaCard persona={persona} onEdit={vi.fn()} onDelete={onDelete} />);
    fireEvent.click(screen.getByRole('button', { name: 'Eliminar persona' }));
    expect(onDelete).toHaveBeenCalled();
  });

  it('lists, then removes with confirm and surfaces the store error', async () => {
    const store = makeStore({ remove: vi.fn(async () => Promise.reject(new Error('Persona protegida'))) });
    let api: ReturnType<typeof usePersonaCollection> | undefined;
    function Probe() {
      api = usePersonaCollection(store, { confirm: async () => true });
      return <ul>{api.personas.map((p) => <li key={p.id}>{p.name}</li>)}</ul>;
    }
    render(<Probe />);
    const list = await screen.findByRole('list');
    expect(within(list).getByText('SOAP Editor')).toBeTruthy();
    let removed: boolean | undefined;
    await act(async () => {
      removed = await api!.remove(persona);
    });
    expect(removed).toBe(false);
    expect(api!.removeError).toBe('Persona protegida');
    expect(within(list).getByText('SOAP Editor')).toBeTruthy();
  });
});
