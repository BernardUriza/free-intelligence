'use client';

import { useId } from 'react';
import { CheckCircle2, FlaskConical, Loader2, X, XCircle } from 'lucide-react';
import { AdminAlert, AdminButton } from '../admin-kit';
import { ModelSheet } from './ModelSheet';
import type { ModelTestState } from './useModelTest';

export type ModelTestSheetProps = Pick<ModelTestState, 'model' | 'running' | 'stage' | 'result' | 'error' | 'close'>;

export function ModelTestSheet({ model, running, stage, result, error, close }: ModelTestSheetProps) {
  const titleId = useId();
  if (!model) return null;
  const failed = result ? !result.success : false;
  return (
    <ModelSheet
      onDismiss={close}
      labelledBy={titleId}
      header={
        <div className="fi-admin-head-row">
          <h2 id={titleId} className="fi-mc-title">
            {running ? (
              <FlaskConical size={20} aria-hidden="true" />
            ) : failed || error ? (
              <XCircle size={20} aria-hidden="true" />
            ) : (
              <CheckCircle2 size={20} aria-hidden="true" />
            )}
            {failed || error ? `Error al probar ${model.id}` : `Prueba de ${model.id}`}
          </h2>
          <AdminButton variant="ghost" iconOnly icon={X} aria-label="Cerrar" onClick={close} />
        </div>
      }
      footer={
        <div className="fi-admin-head-row" style={{ justifyContent: 'flex-end' }}>
          <AdminButton onClick={close}>{running ? 'Cancelar' : 'Cerrar'}</AdminButton>
        </div>
      }
    >
      {running && stage ? (
        <div className="fi-mc-empty" role="status">
          <Loader2 size={32} className="fi-admin-spin" aria-hidden="true" />
          <h3>{stage.title}</h3>
          <p>{stage.text}</p>
        </div>
      ) : null}
      {error ? <AdminAlert>{error}</AdminAlert> : null}
      {result ? (
        <div className="fi-mc-stack">
          <div className="fi-mc-result">
            <span className="fi-mc-label">Prompt</span>
            <p>{result.prompt}</p>
          </div>
          <div className="fi-mc-result" data-tone={result.success ? 'success' : 'error'}>
            <span className="fi-mc-label">{result.success ? 'Respuesta del modelo' : 'Error'}</span>
            <p>{result.success ? result.response : result.error || 'Error desconocido'}</p>
          </div>
        </div>
      ) : null}
    </ModelSheet>
  );
}
