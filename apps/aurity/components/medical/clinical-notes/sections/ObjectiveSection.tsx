/**
 * ObjectiveSection Component
 *
 * SOAP "Objective" section: vital signs + physical exam.
 * SRP: objective data entry UI only.
 *
 * @created 2026-02-22
 */

'use client';

import {
  BarChart3,
  CheckCircle2,
  Thermometer,
  Heart,
  Activity,
  Wind,
  TrendingUp,
  Edit3,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

import type { SOAPData, ClinicalNotesFormHandlers } from '../types';
import { SectionHeader, VitalSignInput } from '../components';

interface ObjectiveSectionProps {
  soapData: SOAPData;
  handlers: Pick<
    ClinicalNotesFormHandlers,
    'updateField' | 'updateVitalSign' | 'fillNormalVitals'
  >;
}

export function ObjectiveSection({
  soapData,
  handlers,
}: ObjectiveSectionProps) {
  return (
    <section className="fi-card-xl" aria-labelledby="objective-heading">
      <SectionHeader
        icon={BarChart3}
        title="Objetivo"
        iconColor="text-cyan-400"
      />
      <h4 id="objective-heading" className="cnotes-sr-only">
        Sección Objetivo
      </h4>

      {/* Vital Signs */}
      <div className="cnotes-field-group">
        <div className="cnotes-vitals-header">
          <span className="cnotes-vitals-label fi-text">Signos Vitales</span>
          <Button
            onClick={handlers.fillNormalVitals}
            variant="ghost"
            size="sm"
            icon={CheckCircle2}
            className="cnotes-fill-normal-btn fi-text-success"
          >
            Llenar valores normales
          </Button>
        </div>

        <div className="cnotes-vitals-grid">
          <VitalSignInput
            icon={Thermometer}
            iconColor="text-red-400"
            label="Temp."
            value={soapData.vitalSigns.temperature}
            onChange={(v) => handlers.updateVitalSign('temperature', v)}
            placeholder="36.5"
            unit="°C"
            step="0.1"
          />
          <VitalSignInput
            icon={Heart}
            iconColor="text-red-400"
            label="FC"
            value={soapData.vitalSigns.heartRate}
            onChange={(v) => handlers.updateVitalSign('heartRate', v)}
            placeholder="72"
            unit="bpm"
            inputWidth="w-12"
          />
          <VitalSignInput
            icon={Activity}
            iconColor="fi-text-primary"
            label="PA"
            value={soapData.vitalSigns.bloodPressure}
            onChange={(v) => handlers.updateVitalSign('bloodPressure', v)}
            placeholder="120/80"
            type="text"
            inputWidth="w-16"
          />
          <VitalSignInput
            icon={Wind}
            iconColor="text-cyan-400"
            label="FR"
            value={soapData.vitalSigns.respiratoryRate}
            onChange={(v) => handlers.updateVitalSign('respiratoryRate', v)}
            placeholder="16"
            unit="/min"
            inputWidth="w-12"
          />
          <VitalSignInput
            icon={TrendingUp}
            iconColor="fi-text-green"
            label="SpO₂"
            value={soapData.vitalSigns.oxygenSaturation}
            onChange={(v) => handlers.updateVitalSign('oxygenSaturation', v)}
            placeholder="98"
            unit="%"
            inputWidth="w-12"
          />
        </div>
      </div>

      {/* Physical Exam */}
      <div>
        <label htmlFor="physical-exam" className="cnotes-exam-label fi-label">
          <Edit3 className="cnotes-exam-icon" aria-hidden="true" />
          Examen Físico
        </label>
        <textarea
          id="physical-exam"
          value={soapData.physicalExam}
          onChange={(e) => handlers.updateField('physicalExam', e.target.value)}
          rows={3}
          placeholder="Descripción del examen físico..."
          className="fi-textarea-cyan"
        />
      </div>
    </section>
  );
}
