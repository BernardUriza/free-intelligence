/**
 * MedicationsTab Component
 *
 * Composes MedicationForm and MedicationList into the medications tab.
 * Single Responsibility: medication entry + list UI orchestration.
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 * @refactored 2026-02-22
 */

"use client";

import type { Medication } from "@/lib/api/prescriptions";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MedicationForm } from "../MedicationForm";
import { MedicationList } from "../MedicationList";
import { Pill } from "lucide-react";

interface MedicationsTabProps {
  medications: Medication[];
  editingMedIndex: number | null;
  onAddMedication: (med: Medication) => void;
  onEditMedication: (index: number) => void;
  onRemoveMedication: (index: number) => void;
  onCancelEdit: () => void;
}

export function MedicationsTab({
  medications,
  editingMedIndex,
  onAddMedication,
  onEditMedication,
  onRemoveMedication,
  onCancelEdit,
}: MedicationsTabProps) {
  const isEditing = editingMedIndex !== null;
  const editingMedication =
    isEditing ? medications[editingMedIndex] : undefined;

  return (
    <div className="rx-med-stack">
      <Card>
        <CardHeader>
          <CardTitle className="rx-section-title">
            <Pill className="rx-section-icon" />
            {isEditing
              ? `Editando Medicamento ${editingMedIndex + 1}`
              : "Agregar Medicamento"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <MedicationForm
            medication={editingMedication}
            onSave={onAddMedication}
            onCancel={isEditing ? onCancelEdit : undefined}
            isEditing={isEditing}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            Medicamentos en la Receta ({medications.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <MedicationList
            medications={medications}
            onEdit={onEditMedication}
            onRemove={onRemoveMedication}
          />
        </CardContent>
      </Card>
    </div>
  );
}
