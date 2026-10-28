'use client';

import { useId, useState } from 'react';
import { List, Plus, Trash2, Zap } from 'lucide-react';
import { Alert, FieldLabel, PersonaButton } from './controls';
import { errorMessage, type Persona, type PersonaExample, type PersonaStore, type PersonaTestResponse } from './types';

type PersonaPatch = (updates: Partial<Persona>) => void;

export function PersonaPromptTab({ persona, onChange }: { persona: Persona; onChange: PersonaPatch }) {
  const id = useId();
  return (
    <div className="fi-persona-field">
      <div className="fi-persona-hint">
        <FieldLabel htmlFor={id}>System Prompt</FieldLabel>
        <span>{persona.system_prompt.length} caracteres</span>
      </div>
      <textarea
        id={id}
        className="fi-persona-input fi-persona-mono"
        rows={22}
        value={persona.system_prompt}
        onChange={(e) => onChange({ system_prompt: e.target.value })}
        placeholder="Eres un..."
      />
    </div>
  );
}

function outputText(output: PersonaExample['output']): string {
  return typeof output === 'string' ? output : JSON.stringify(output, null, 2);
}

export function PersonaExamplesTab({ persona, onChange }: { persona: Persona; onChange: PersonaPatch }) {
  const uid = useId();
  const examples = persona.examples;
  const update = (index: number, field: 'input' | 'output', value: string) =>
    onChange({ examples: examples.map((ex, i) => (i === index ? { ...ex, [field]: value } : ex)) });

  return (
    <div className="fi-persona-stack">
      <div className="fi-persona-hint">
        <h3 className="fi-persona-title">Few-shot examples ({examples.length})</h3>
        <PersonaButton icon={Plus} onClick={() => onChange({ examples: [...examples, { input: '', output: '' }] })}>
          Agregar example
        </PersonaButton>
      </div>
      {examples.length === 0 ? (
        <div className="fi-persona-empty">
          <List size={40} aria-hidden="true" />
          <p>No hay examples configurados</p>
          <p>Agrega examples para mejorar la precisión de la persona</p>
        </div>
      ) : (
        examples.map((example, index) => (
          <div key={index} className="fi-persona-example">
            <div className="fi-persona-hint">
              <strong>Example {index + 1}</strong>
              <PersonaButton
                variant="ghost"
                iconOnly
                icon={Trash2}
                aria-label={`Eliminar example ${index + 1}`}
                onClick={() => onChange({ examples: examples.filter((_, i) => i !== index) })}
              />
            </div>
            <div className="fi-persona-field">
              <FieldLabel htmlFor={`${uid}-in-${index}`}>Input</FieldLabel>
              <textarea
                id={`${uid}-in-${index}`}
                className="fi-persona-input fi-persona-mono"
                rows={3}
                value={example.input}
                onChange={(e) => update(index, 'input', e.target.value)}
                placeholder="Entrada de ejemplo..."
              />
            </div>
            <div className="fi-persona-field">
              <FieldLabel htmlFor={`${uid}-out-${index}`}>Output</FieldLabel>
              <textarea
                id={`${uid}-out-${index}`}
                className="fi-persona-input fi-persona-mono"
                rows={3}
                value={outputText(example.output)}
                onChange={(e) => update(index, 'output', e.target.value)}
                placeholder="Salida esperada..."
              />
            </div>
          </div>
        ))
      )}
    </div>
  );
}

export function PersonaTestTab({ personaId, store }: { personaId: string; store: Pick<PersonaStore, 'test'> }) {
  const id = useId();
  const [input, setInput] = useState('');
  const [result, setResult] = useState<PersonaTestResponse | null>(null);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!input.trim()) return;
    setTesting(true);
    setError(null);
    try {
      setResult(await store.test(personaId, input));
    } catch (err) {
      setError(errorMessage(err, 'Error al probar la persona'));
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="fi-persona-stack">
      <div>
        <h3 className="fi-persona-title">Probar persona</h3>
        <p className="fi-persona-subtitle">Prueba la persona con un input de ejemplo para ver cómo responde</p>
      </div>
      <div className="fi-persona-field">
        <FieldLabel htmlFor={id}>Input de prueba</FieldLabel>
        <textarea
          id={id}
          className="fi-persona-input"
          rows={6}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ingresa un caso de prueba..."
        />
      </div>
      <PersonaButton variant="primary" icon={Zap} loading={testing} disabled={testing || !input.trim()} onClick={() => void run()}>
        {testing ? 'Probando...' : 'Probar persona'}
      </PersonaButton>
      {error ? <Alert>{error}</Alert> : null}
      {result ? (
        <div className="fi-persona-stack">
          <h4 className="fi-persona-title">Resultado</h4>
          <pre className="fi-persona-pre" data-testid="persona-test-output">
            {typeof result.output === 'string' ? result.output : JSON.stringify(result.output, null, 2)}
          </pre>
          <div className="fi-persona-card-stats">
            <div className="fi-persona-row">
              <span>Latencia</span>
              <b>{result.latency_ms.toFixed(0)}ms</b>
            </div>
            {result.tokens_used !== undefined ? (
              <div className="fi-persona-row">
                <span>Tokens</span>
                <b>{result.tokens_used}</b>
              </div>
            ) : null}
            {result.cost_usd !== undefined ? (
              <div className="fi-persona-row">
                <span>Costo</span>
                <b>${result.cost_usd.toFixed(4)}</b>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
