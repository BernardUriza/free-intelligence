'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { isLocalProvider } from './format';
import { errorMessage, type LLMModel, type ModelCatalogStore, type ModelTestResult } from './types';

export interface ModelTestStage {
  title: string;
  text: string;
  /** Milliseconds after the test starts at which this stage is shown. */
  delay: number;
}

export function modelTestStages(model: LLMModel): ModelTestStage[] {
  if (isLocalProvider(model.provider)) {
    return [
      { title: `Probando ${model.label}...`, text: 'Iniciando conexión con Ollama', delay: 0 },
      { title: 'Cargando modelo en memoria...', text: 'Los modelos locales requieren cargarse en RAM', delay: 3000 },
      { title: 'Generando respuesta...', text: 'Esto puede tardar varios minutos para modelos grandes', delay: 15000 },
      { title: 'Procesando...', text: 'El modelo está respondiendo a la consulta', delay: 60000 },
      { title: 'Casi listo...', text: 'Finalizando generación de respuesta', delay: 180000 },
    ];
  }
  return [
    { title: `Probando ${model.label}...`, text: 'Conectando con la API', delay: 0 },
    { title: 'Generando respuesta...', text: 'El modelo está procesando la consulta', delay: 3000 },
  ];
}

export interface ModelTestState {
  model: LLMModel | null;
  running: boolean;
  stage: ModelTestStage | null;
  result: ModelTestResult | null;
  error: string | null;
  run: (model: LLMModel) => Promise<void>;
  close: () => void;
}

export function useModelTest(store: Pick<ModelCatalogStore, 'testModel'>): ModelTestState {
  const storeRef = useRef(store);
  storeRef.current = store;
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const runId = useRef(0);
  const [model, setModel] = useState<LLMModel | null>(null);
  const [running, setRunning] = useState(false);
  const [stage, setStage] = useState<ModelTestStage | null>(null);
  const [result, setResult] = useState<ModelTestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const clearTimers = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  const run = useCallback(
    async (next: LLMModel) => {
      clearTimers();
      const id = ++runId.current;
      const stages = modelTestStages(next);
      setModel(next);
      setResult(null);
      setError(null);
      setRunning(true);
      setStage(stages[0]);
      timers.current = stages.slice(1).map((s) => setTimeout(() => setStage(s), s.delay));
      try {
        const outcome = await storeRef.current.testModel(next.id);
        if (id === runId.current) setResult(outcome);
      } catch (err) {
        if (id === runId.current) setError(errorMessage(err, 'Error al probar el modelo'));
      } finally {
        if (id === runId.current) {
          clearTimers();
          setRunning(false);
          setStage(null);
        }
      }
    },
    [clearTimers],
  );

  const close = useCallback(() => {
    runId.current += 1;
    clearTimers();
    setModel(null);
    setRunning(false);
    setStage(null);
    setResult(null);
    setError(null);
  }, [clearTimers]);

  return { model, running, stage, result, error, run, close };
}
