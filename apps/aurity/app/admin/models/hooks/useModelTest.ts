/**
 * useModelTest Hook
 *
 * Single Responsibility: LLM model test flow with progressive loading UI.
 * Handles local (Ollama) vs cloud model stage differences.
 *
 * Route: /admin/models
 */

'use client';

import { useCallback } from 'react';
import type { LLMModel } from '@aurity-standalone/types/llm';
import { testLLMModel } from '@aurity-standalone/api-client/llm-models';
import { toastError, swal, showProgressiveLoading, closeDialog } from '@/lib/swal';

/** Progressive loading stages for local Ollama models. */
function getLocalStages(label: string) {
  return [
    { title: `Probando ${label}...`, text: 'Iniciando conexión con Ollama', delay: 0 },
    { title: 'Cargando modelo en memoria...', text: 'Los modelos locales requieren cargarse en RAM', delay: 3000 },
    { title: 'Generando respuesta...', text: 'Esto puede tardar varios minutos para modelos grandes', delay: 15000 },
    { title: 'Procesando...', text: 'El modelo está respondiendo a la consulta médica', delay: 60000 },
    { title: 'Casi listo...', text: 'Finalizando generación de respuesta', delay: 180000 },
  ];
}

/** Progressive loading stages for cloud API models. */
function getCloudStages(label: string) {
  return [
    { title: `Probando ${label}...`, text: 'Conectando con API', delay: 0 },
    { title: 'Generando respuesta...', text: 'El modelo está procesando la consulta', delay: 3000 },
  ];
}

/** Build the SweetAlert HTML for test results. */
function buildResultHtml(result: { success: boolean; prompt: string; response?: string; error?: string | null }) {
  if (result.success) {
    return `
      <div class="mdl-swal-body">
        <div class="mdl-swal-prompt">
          <p class="mdl-swal-label">Prompt médico</p>
          <p class="mdl-swal-text">${result.prompt}</p>
        </div>
        <div class="mdl-swal-success-box">
          <p class="mdl-swal-success-label">Respuesta del modelo</p>
          <p class="mdl-swal-response-text">${result.response}</p>
        </div>
      </div>
    `;
  }
  return `
    <div class="mdl-swal-body">
      <div class="mdl-swal-prompt">
        <p class="mdl-swal-label">Prompt</p>
        <p class="mdl-swal-text">${result.prompt}</p>
      </div>
      <div class="mdl-swal-error-box">
        <p class="mdl-swal-error-label">Error</p>
        <p class="mdl-swal-error-text">${result.error || 'Error desconocido'}</p>
      </div>
    </div>
  `;
}

export function useModelTest() {
  const handleTest = useCallback(async (model: LLMModel) => {
    const isLocal = model.provider === 'ollama';
    const stages = isLocal ? getLocalStages(model.label) : getCloudStages(model.label);
    const progressController = showProgressiveLoading(stages);

    try {
      const result = await testLLMModel(model.id);
      progressController.stop();
      closeDialog();

      await swal.fire({
        icon: result.success ? 'success' : 'error',
        title: result.success ? `Prueba de ${model.id}` : `Error al probar ${model.id}`,
        html: buildResultHtml(result),
        confirmButtonText: 'Cerrar',
        width: '600px',
      });
    } catch (err) {
      progressController.stop();
      closeDialog();
      console.error('Failed to test model:', err);
      toastError(err instanceof Error ? err.message : 'Error al probar el modelo');
    }
  }, []);

  return { handleTest } as const;
}
