/**
 * SubjectiveSection Component
 *
 * SOAP "Subjective" section: chief complaint, HPI, allergies,
 * current medications.
 * SRP: subjective data entry UI only.
 *
 * @created 2026-02-22
 */

'use client';

import type { ChangeEvent, KeyboardEvent } from 'react';
import { useCallback } from 'react';
import {
  MessageSquare,
  Mic,
  MicOff,
  Plus,
  X,
  Pill,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

import type { SOAPData } from '../types';
import type { ClinicalNotesFormHandlers, ClinicalNotesFormState } from '../types';
import { SectionHeader, TagList } from '../components';

interface SubjectiveSectionProps {
  soapData: SOAPData;
  newAllergy: string;
  voiceActive: string | null;
  handlers: Pick<
    ClinicalNotesFormHandlers,
    | 'updateField'
    | 'addAllergy'
    | 'removeAllergy'
    | 'setNewAllergy'
    | 'setVoiceActive'
  >;
}

export function SubjectiveSection({
  soapData,
  newAllergy,
  voiceActive,
  handlers,
}: SubjectiveSectionProps) {
  const handleKeyPress = useCallback(
    (e: KeyboardEvent<HTMLInputElement>, action: () => void) => {
      if (e.key === 'Enter') action();
    },
    [],
  );

  return (
    <section className="fi-card-xl" aria-labelledby="subjective-heading">
      <SectionHeader
        icon={MessageSquare}
        title="Subjetivo"
        iconColor="text-blue-400"
      />
      <h4 id="subjective-heading" className="cnotes-sr-only">
        Sección Subjetivo
      </h4>

      {/* Chief Complaint */}
      <div className="cnotes-field-group">
        <label htmlFor="chief-complaint" className="fi-label">
          Motivo de Consulta *
        </label>
        <div className="cnotes-input-row">
          <Input
            id="chief-complaint"
            type="text"
            value={soapData.chiefComplaint}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              handlers.updateField('chiefComplaint', e.target.value)
            }
            placeholder="Ej: Dolor de garganta por 3 días"
            className="cnotes-input-flex"
          />
          <Button
            onClick={() =>
              handlers.setVoiceActive((prev) =>
                prev === 'chief' ? null : 'chief',
              )
            }
            variant={voiceActive === 'chief' ? 'danger' : 'secondary'}
            icon={voiceActive === 'chief' ? MicOff : Mic}
            aria-label={
              voiceActive === 'chief'
                ? 'Desactivar dictado'
                : 'Activar dictado'
            }
          />
        </div>
      </div>

      {/* HPI */}
      <div className="cnotes-field-group">
        <label htmlFor="hpi" className="fi-label">
          Historia de Enfermedad Actual
        </label>
        <textarea
          id="hpi"
          value={soapData.hpi}
          onChange={(e) => handlers.updateField('hpi', e.target.value)}
          rows={3}
          placeholder="Descripción detallada de síntomas..."
          className="fi-textarea-blue"
        />
      </div>

      {/* Allergies */}
      <div className="cnotes-field-group">
        <label className="fi-label">Alergias</label>
        <TagList items={soapData.allergies} onRemove={handlers.removeAllergy} />
        <div className="cnotes-input-row">
          <Input
            type="text"
            value={newAllergy}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              handlers.setNewAllergy(e.target.value)
            }
            onKeyPress={(e: KeyboardEvent<HTMLInputElement>) =>
              handleKeyPress(e, handlers.addAllergy)
            }
            placeholder="Agregar alergia..."
            className="cnotes-input-flex"
          />
          <Button onClick={handlers.addAllergy} variant="primary" icon={Plus} />
        </div>
      </div>

      {/* Current Medications */}
      <div>
        <label className="fi-label">Medicamentos Actuales</label>
        {soapData.currentMedications.length > 0 && (
          <div className="cnotes-med-list">
            {soapData.currentMedications.map((med, idx) => (
              <div key={`current-med-${idx}`} className="cnotes-med-item">
                <Pill
                  className="cnotes-med-icon fi-text-primary"
                  aria-hidden="true"
                />
                <span className="cnotes-med-name">{med}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  icon={X}
                  className="cnotes-remove-btn"
                  aria-label={`Eliminar ${med}`}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
