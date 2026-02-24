/**
 * PlanSection Component
 *
 * SOAP "Plan" section: medications, diagnostic tests, follow-up.
 * SRP: plan data entry UI only.
 *
 * @created 2026-02-22
 */

'use client';

import type { ChangeEvent } from 'react';
import { ClipboardList, Plus, X, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

import type { SOAPData, Medication, ClinicalNotesFormHandlers } from '../types';
import { COMMON_DIAGNOSTIC_TESTS } from '../constants';
import { SectionHeader, MedicationList } from '../components';

interface PlanSectionProps {
  soapData: SOAPData;
  newMedication: Medication;
  showChatbot: boolean;
  handlers: Pick<
    ClinicalNotesFormHandlers,
    | 'updateField'
    | 'addMedication'
    | 'removeMedication'
    | 'setNewMedication'
    | 'toggleDiagnosticTest'
    | 'removeDiagnosticTest'
    | 'setShowChatbot'
  >;
}

export function PlanSection({
  soapData,
  newMedication,
  showChatbot,
  handlers,
}: PlanSectionProps) {
  return (
    <section className="fi-card-xl" aria-labelledby="plan-heading">
      <SectionHeader
        icon={ClipboardList}
        title="Plan"
        iconColor="text-emerald-400"
        action={
          <Button
            onClick={() => handlers.setShowChatbot((prev) => !prev)}
            variant={showChatbot ? 'success' : 'secondary'}
            size="sm"
            icon={Zap}
          >
            Asistente IA
          </Button>
        }
      />
      <h4 id="plan-heading" className="cnotes-sr-only">
        Sección Plan
      </h4>

      {/* Medications */}
      <MedicationFormBlock
        medications={soapData.medications}
        newMedication={newMedication}
        onAdd={handlers.addMedication}
        onRemove={handlers.removeMedication}
        onNewMedChange={handlers.setNewMedication}
      />

      {/* Diagnostic Tests */}
      <DiagnosticTestsBlock
        selectedTests={soapData.diagnosticTests}
        onToggle={handlers.toggleDiagnosticTest}
        onRemove={handlers.removeDiagnosticTest}
      />

      {/* Follow-up */}
      <div>
        <label htmlFor="follow-up" className="fi-label">
          Seguimiento
        </label>
        <textarea
          id="follow-up"
          value={soapData.followUp}
          onChange={(e) => handlers.updateField('followUp', e.target.value)}
          rows={2}
          placeholder="Instrucciones de seguimiento..."
          className="fi-textarea-blue"
        />
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Co-located sub-components
// ---------------------------------------------------------------------------

function MedicationFormBlock({
  medications,
  newMedication,
  onAdd,
  onRemove,
  onNewMedChange,
}: {
  medications: Medication[];
  newMedication: Medication;
  onAdd: () => void;
  onRemove: (index: number) => void;
  onNewMedChange: React.Dispatch<React.SetStateAction<Medication>>;
}) {
  return (
    <div className="cnotes-field-group">
      <span className="fi-label">Tratamiento Farmacológico</span>
      <MedicationList medications={medications} onRemove={onRemove} />
      <div className="cnotes-med-form-grid">
        <Input
          type="text"
          value={newMedication.name}
          onChange={(e: ChangeEvent<HTMLInputElement>) =>
            onNewMedChange((prev) => ({ ...prev, name: e.target.value }))
          }
          placeholder="Medicamento"
        />
        <Input
          type="text"
          value={newMedication.dose}
          onChange={(e: ChangeEvent<HTMLInputElement>) =>
            onNewMedChange((prev) => ({ ...prev, dose: e.target.value }))
          }
          placeholder="Dosis"
        />
        <Input
          type="text"
          value={newMedication.frequency}
          onChange={(e: ChangeEvent<HTMLInputElement>) =>
            onNewMedChange((prev) => ({ ...prev, frequency: e.target.value }))
          }
          placeholder="Frecuencia"
        />
      </div>
      <Button onClick={onAdd} variant="primary" icon={Plus} size="sm">
        Agregar medicamento
      </Button>
    </div>
  );
}

function DiagnosticTestsBlock({
  selectedTests,
  onToggle,
  onRemove,
}: {
  selectedTests: string[];
  onToggle: (test: string) => void;
  onRemove: (index: number) => void;
}) {
  return (
    <div className="cnotes-field-group">
      <span className="fi-label">Estudios de Laboratorio / Gabinete</span>
      <div className="cnotes-test-list">
        {COMMON_DIAGNOSTIC_TESTS.map((test) => (
          <label key={test} className="cnotes-test-item">
            <input
              type="checkbox"
              checked={selectedTests.includes(test)}
              onChange={() => onToggle(test)}
              className="cnotes-test-checkbox"
            />
            <span className="cnotes-test-label">{test}</span>
          </label>
        ))}
      </div>

      {selectedTests.length > 0 && (
        <div className="cnotes-orders-section">
          <span className="cnotes-orders-label">Órdenes Seleccionadas:</span>
          <div className="cnotes-orders-list">
            {selectedTests.map((test, idx) => (
              <div key={`selected-test-${idx}`} className="cnotes-order-item">
                <div className="fi-flex-between">
                  <span className="cnotes-order-name">{test}</span>
                  <Button
                    onClick={() => onRemove(idx)}
                    variant="ghost"
                    size="sm"
                    icon={X}
                    className="cnotes-remove-btn"
                    aria-label={`Eliminar ${test}`}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
