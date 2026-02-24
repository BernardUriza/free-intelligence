/**
 * AssessmentSection Component
 *
 * SOAP "Assessment" section: ICD-10 search, primary diagnosis,
 * differential diagnoses.
 * SRP: assessment data entry UI only.
 *
 * @created 2026-02-22
 */

'use client';

import { useMemo, type ChangeEvent } from 'react';
import { Search, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

import type { SOAPData, Diagnosis, ClinicalNotesFormHandlers } from '../types';
import { COMMON_ICD10 } from '../constants';
import { getSeverityStyles } from '../utils';
import { SectionHeader } from '../components';

interface AssessmentSectionProps {
  soapData: SOAPData;
  icd10Search: string;
  showICD10Dropdown: boolean;
  handlers: Pick<
    ClinicalNotesFormHandlers,
    | 'selectDiagnosis'
    | 'clearPrimaryDiagnosis'
    | 'removeDifferentialDiagnosis'
    | 'setICD10Search'
    | 'setShowICD10Dropdown'
  >;
}

export function AssessmentSection({
  soapData,
  icd10Search,
  showICD10Dropdown,
  handlers,
}: AssessmentSectionProps) {
  const filteredICD10 = useMemo(() => {
    if (!icd10Search.trim()) return [];
    const search = icd10Search.toLowerCase();
    return COMMON_ICD10.filter(
      (d) =>
        d.code.toLowerCase().includes(search) ||
        d.description.toLowerCase().includes(search),
    );
  }, [icd10Search]);

  return (
    <section className="fi-card-xl" aria-labelledby="assessment-heading">
      <SectionHeader
        icon={Search}
        title="Evaluación"
        iconColor="text-purple-400"
      />
      <h4 id="assessment-heading" className="cnotes-sr-only">
        Sección Evaluación
      </h4>

      {/* ICD-10 Search + Primary Diagnosis */}
      <div className="cnotes-field-group">
        <label htmlFor="icd10-search" className="fi-label">
          Diagnóstico Principal
        </label>
        <div className="cnotes-relative">
          <Input
            id="icd10-search"
            type="text"
            value={icd10Search}
            onChange={(e: ChangeEvent<HTMLInputElement>) => {
              handlers.setICD10Search(e.target.value);
              handlers.setShowICD10Dropdown(true);
            }}
            onFocus={() => handlers.setShowICD10Dropdown(true)}
            icon={Search}
            placeholder="Buscar diagnóstico por código ICD-10 o nombre..."
          />

          {showICD10Dropdown && filteredICD10.length > 0 && (
            <ICD10Dropdown
              results={filteredICD10}
              onSelect={handlers.selectDiagnosis}
            />
          )}
        </div>

        {soapData.primaryDiagnosis && (
          <PrimaryDiagnosisBadge
            diagnosis={soapData.primaryDiagnosis}
            onClear={handlers.clearPrimaryDiagnosis}
          />
        )}
      </div>

      {/* Differential Diagnoses */}
      {soapData.differentialDiagnoses.length > 0 && (
        <DifferentialDiagnosesList
          diagnoses={soapData.differentialDiagnoses}
          onRemove={handlers.removeDifferentialDiagnosis}
        />
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Co-located sub-components (small, tightly coupled to this section)
// ---------------------------------------------------------------------------

function ICD10Dropdown({
  results,
  onSelect,
}: {
  results: Diagnosis[];
  onSelect: (d: Diagnosis) => void;
}) {
  return (
    <div className="fi-dropdown" role="listbox">
      {results.map((diagnosis) => (
        <button
          key={diagnosis.code}
          type="button"
          onClick={() => onSelect(diagnosis)}
          className="cnotes-dropdown-item cnotes-dropdown-item-border"
          role="option"
          aria-selected={false}
        >
          <div className="fi-flex-between">
            <div>
              <span className="cnotes-dropdown-code">{diagnosis.code}</span>
              <span className="cnotes-dropdown-desc">
                {diagnosis.description}
              </span>
            </div>
            <span
              className={`cnotes-severity-badge ${getSeverityStyles(diagnosis.severity)}`}
            >
              {diagnosis.severity}
            </span>
          </div>
        </button>
      ))}
    </div>
  );
}

function PrimaryDiagnosisBadge({
  diagnosis,
  onClear,
}: {
  diagnosis: Diagnosis;
  onClear: () => void;
}) {
  return (
    <div className="cnotes-primary-dx">
      <div className="fi-flex-between">
        <div>
          <span className="fi-text-purple cnotes-dx-code">
            {diagnosis.code}
          </span>
          <span className="cnotes-dx-desc">{diagnosis.description}</span>
        </div>
        <Button
          onClick={onClear}
          variant="ghost"
          size="sm"
          icon={X}
          className="cnotes-remove-btn"
          aria-label="Eliminar diagnóstico principal"
        />
      </div>
    </div>
  );
}

function DifferentialDiagnosesList({
  diagnoses,
  onRemove,
}: {
  diagnoses: Diagnosis[];
  onRemove: (index: number) => void;
}) {
  return (
    <div className="cnotes-diff-section">
      <span className="fi-label">Diagnósticos Diferenciales</span>
      <div className="cnotes-diff-list">
        {diagnoses.map((diff, idx) => (
          <div key={`diff-${idx}`} className="cnotes-diff-item">
            <div className="fi-flex-between">
              <div>
                {diff.code && (
                  <span className="fi-text-purple cnotes-diff-code">
                    {diff.code}
                  </span>
                )}
                <span className="cnotes-diff-desc">{diff.description}</span>
              </div>
              <Button
                onClick={() => onRemove(idx)}
                variant="ghost"
                size="sm"
                icon={X}
                className="cnotes-remove-btn"
                aria-label={`Eliminar ${diff.description}`}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
