/**
 * MedicationList Component
 *
 * Displays a list of medications with edit/remove actions.
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 */

"use client";

import { Button } from "@/components/ui/button";
import {
  Medication,
  FREQUENCY_LABELS,
  ROUTE_LABELS,
} from "@/lib/api/prescriptions";
import { Pill, Edit2, Trash2, GripVertical, AlertTriangle } from "lucide-react";

interface MedicationListProps {
  medications: Medication[];
  onEdit?: (index: number) => void;
  onRemove?: (index: number) => void;
  readonly?: boolean;
}

export function MedicationList({
  medications,
  onEdit,
  onRemove,
  readonly = false,
}: MedicationListProps) {
  if (medications.length === 0) {
    return (
      <div className="rx-list-empty">
        <Pill className="rx-list-empty-icon" />
        <p className="text-sm">No hay medicamentos agregados</p>
        <p className="text-xs mt-1">
          Use el formulario para agregar medicamentos a la receta
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {medications.map((med, index) => (
        <MedicationCard
          key={`${med.name}-${index}`}
          medication={med}
          index={index}
          onEdit={onEdit}
          onRemove={onRemove}
          readonly={readonly}
        />
      ))}
    </div>
  );
}

interface MedicationCardProps {
  medication: Medication;
  index: number;
  onEdit?: (index: number) => void;
  onRemove?: (index: number) => void;
  readonly?: boolean;
}

function MedicationCard({
  medication,
  index,
  onEdit,
  onRemove,
  readonly,
}: MedicationCardProps) {
  const frequencyLabel =
    medication.frequency === "custom" && medication.frequency_custom
      ? medication.frequency_custom
      : FREQUENCY_LABELS[medication.frequency];

  const routeLabel = ROUTE_LABELS[medication.route];

  const durationLabel = medication.duration_text
    ? medication.duration_text
    : medication.duration_days
    ? `${medication.duration_days} dias`
    : "Segun indicacion";

  return (
    <div className="group rx-list-card">
      {/* Drag Handle (for future drag-drop) */}
      {!readonly && (
        <div className="rx-list-drag-handle">
          <GripVertical className="w-4 h-4 text-slate-400" />
        </div>
      )}

      {/* Index Badge */}
      <div className="rx-list-index-badge">
        <span className="rx-list-index-text">
          {index + 1}
        </span>
      </div>

      {/* Medication Info */}
      <div className="rx-list-info">
        <div className="rx-list-header">
          <h4 className="rx-list-name">
            {medication.name}
          </h4>
          <span className="rx-list-dosage">
            {medication.dosage}
          </span>
          {medication.dosage_form && (
            <span className="rx-list-form-badge">
              {medication.dosage_form}
            </span>
          )}
        </div>

        <div className="rx-list-details">
          <span>{routeLabel}</span>
          <span className="rx-list-separator">&bull;</span>
          <span>{frequencyLabel}</span>
          <span className="rx-list-separator">&bull;</span>
          <span>{durationLabel}</span>
          {medication.quantity && (
            <>
              <span className="rx-list-separator">&bull;</span>
              <span className="rx-list-quantity">
                {medication.quantity}
              </span>
            </>
          )}
        </div>

        {medication.instructions && (
          <p className="rx-list-instructions">
            &quot;{medication.instructions}&quot;
          </p>
        )}

        {medication.warnings && (
          <p className="rx-list-warning">
            <AlertTriangle className="w-3 h-3" strokeWidth={1.5} aria-hidden="true" />
            {medication.warnings}
          </p>
        )}
      </div>

      {/* Action Buttons */}
      {!readonly && (
        <div className="rx-list-actions">
          {onEdit && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onEdit(index)}
              className="rx-list-action-btn"
              title="Editar medicamento"
            >
              <Edit2 className="rx-list-edit-icon" />
            </Button>
          )}
          {onRemove && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onRemove(index)}
              className="rx-list-action-btn"
              title="Eliminar medicamento"
            >
              <Trash2 className="rx-list-delete-icon" />
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
