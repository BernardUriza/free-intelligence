/**
 * ActionBar Component
 *
 * Bottom action buttons: Previous, Save, Continue + save status message.
 * SRP: navigation + save actions UI.
 *
 * @created 2026-02-22
 */

'use client';

import { Save, CheckCircle2, ChevronRight, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

import type { SaveMessage } from '../types';

interface ActionBarProps {
  isComplete: boolean;
  isSaving: boolean;
  isSaved: boolean;
  saveMessage: SaveMessage | null;
  onPrevious?: () => void;
  onNext?: () => void;
  onSave: () => void;
}

export function ActionBar({
  isComplete,
  isSaving,
  isSaved,
  saveMessage,
  onPrevious,
  onNext,
  onSave,
}: ActionBarProps) {
  return (
    <>
      <div className="cnotes-actions">
        {onPrevious && (
          <Button
            onClick={onPrevious}
            variant="secondary"
            size="lg"
            className="cnotes-input-flex"
          >
            Anterior
          </Button>
        )}
        <Button
          onClick={onSave}
          disabled={!isComplete || isSaving}
          variant={isComplete ? 'primary' : 'secondary'}
          size="lg"
          icon={isSaving ? undefined : isSaved ? CheckCircle2 : Save}
          loading={isSaving}
          className="cnotes-input-flex"
        >
          {isSaving ? 'Guardando...' : isSaved ? 'Guardado' : 'Guardar Notas'}
        </Button>
        {onNext && (
          <Button
            onClick={onNext}
            disabled={!isComplete}
            variant={isComplete ? 'primary' : 'secondary'}
            size="lg"
            icon={ChevronRight}
            className="cnotes-input-flex"
          >
            Continuar
          </Button>
        )}
      </div>

      {saveMessage && <SaveMessageBanner message={saveMessage} />}
    </>
  );
}

// ---------------------------------------------------------------------------
// Co-located sub-component
// ---------------------------------------------------------------------------

function SaveMessageBanner({ message }: { message: SaveMessage }) {
  const isSuccess = message.type === 'success';

  return (
    <div
      className={`cnotes-save-msg ${isSuccess ? 'cnotes-save-msg-success' : 'cnotes-save-msg-error'}`}
      role="alert"
    >
      {isSuccess ? (
        <CheckCircle2
          className="cnotes-save-icon fi-text-success"
          aria-hidden="true"
        />
      ) : (
        <AlertCircle className="cnotes-save-icon-error" aria-hidden="true" />
      )}
      <p
        className={
          isSuccess
            ? 'cnotes-save-text fi-text-success'
            : 'cnotes-save-text-error'
        }
      >
        {message.text}
      </p>
    </div>
  );
}
