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
import { Pill, Edit2, Trash2, GripVertical } from "lucide-react";

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
      <div className="text-center py-8 text-slate-500 dark:text-slate-400">
        <Pill className="w-12 h-12 mx-auto mb-3 opacity-30" />
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
    ? `${medication.duration_days} días`
    : "Según indicación";

  return (
    <div className="group relative flex items-start gap-3 p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 transition-colors">
      {/* Drag Handle (for future drag-drop) */}
      {!readonly && (
        <div className="absolute left-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-50 cursor-grab">
          <GripVertical className="w-4 h-4 text-slate-400" />
        </div>
      )}

      {/* Index Badge */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
        <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">
          {index + 1}
        </span>
      </div>

      {/* Medication Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <h4 className="font-medium text-slate-900 dark:text-white truncate">
            {medication.name}
          </h4>
          <span className="text-sm text-slate-500 dark:text-slate-400">
            {medication.dosage}
          </span>
          {medication.dosage_form && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
              {medication.dosage_form}
            </span>
          )}
        </div>

        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-600 dark:text-slate-400">
          <span>{routeLabel}</span>
          <span className="text-slate-300 dark:text-slate-600">•</span>
          <span>{frequencyLabel}</span>
          <span className="text-slate-300 dark:text-slate-600">•</span>
          <span>{durationLabel}</span>
          {medication.quantity && (
            <>
              <span className="text-slate-300 dark:text-slate-600">•</span>
              <span className="text-blue-600 dark:text-blue-400">
                {medication.quantity}
              </span>
            </>
          )}
        </div>

        {medication.instructions && (
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 italic">
            &quot;{medication.instructions}&quot;
          </p>
        )}

        {medication.warnings && (
          <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
            ⚠️ {medication.warnings}
          </p>
        )}
      </div>

      {/* Action Buttons */}
      {!readonly && (
        <div className="flex-shrink-0 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {onEdit && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onEdit(index)}
              className="h-8 w-8 p-0"
              title="Editar medicamento"
            >
              <Edit2 className="w-4 h-4 text-slate-500 hover:text-blue-500" />
            </Button>
          )}
          {onRemove && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onRemove(index)}
              className="h-8 w-8 p-0"
              title="Eliminar medicamento"
            >
              <Trash2 className="w-4 h-4 text-slate-500 hover:text-red-500" />
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
