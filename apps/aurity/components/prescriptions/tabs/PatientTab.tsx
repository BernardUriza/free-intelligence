/**
 * PatientTab Component
 *
 * Patient information form including allergies management.
 * Single Responsibility: patient data entry UI.
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 * @refactored 2026-02-22
 */

"use client";

import type { PatientInfo } from "@/lib/api/prescriptions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { User } from "lucide-react";

interface PatientTabProps {
  patient: PatientInfo;
  allergyInput: string;
  onPatientChange: React.Dispatch<React.SetStateAction<PatientInfo>>;
  onAllergyInputChange: (value: string) => void;
  onAddAllergy: () => void;
  onRemoveAllergy: (allergy: string) => void;
}

export function PatientTab({
  patient,
  allergyInput,
  onPatientChange,
  onAllergyInputChange,
  onAddAllergy,
  onRemoveAllergy,
}: PatientTabProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="rx-section-title">
          <User className="rx-section-icon" />
          Información del Paciente
        </CardTitle>
      </CardHeader>
      <CardContent className="rx-field-group">
        <div className="rx-fields-2col">
          <div className="rx-field">
            <Label htmlFor="patient-name">
              Nombre Completo <span className="rx-required">*</span>
            </Label>
            <Input
              id="patient-name"
              value={patient.name}
              onChange={(e) =>
                onPatientChange((p) => ({ ...p, name: e.target.value }))
              }
              placeholder="Nombre del paciente"
            />
          </div>
          <div className="rx-field">
            <Label htmlFor="patient-age">Edad</Label>
            <Input
              id="patient-age"
              value={patient.age ?? ""}
              onChange={(e) =>
                onPatientChange((p) => ({ ...p, age: e.target.value }))
              }
              placeholder="Ej: 45 años"
            />
          </div>
          <div className="rx-field">
            <Label htmlFor="patient-weight">Peso (kg)</Label>
            <Input
              id="patient-weight"
              type="number"
              value={patient.weight_kg ?? ""}
              onChange={(e) =>
                onPatientChange((p) => ({
                  ...p,
                  weight_kg: e.target.value
                    ? parseFloat(e.target.value)
                    : undefined,
                }))
              }
              placeholder="Ej: 70"
            />
          </div>
          <div className="rx-field">
            <Label htmlFor="patient-gender">Género</Label>
            <Input
              id="patient-gender"
              value={patient.gender ?? ""}
              onChange={(e) =>
                onPatientChange((p) => ({ ...p, gender: e.target.value }))
              }
              placeholder="Ej: Femenino"
            />
          </div>
        </div>

        {/* Allergies */}
        <AllergyField
          allergies={patient.allergies}
          inputValue={allergyInput}
          onInputChange={onAllergyInputChange}
          onAdd={onAddAllergy}
          onRemove={onRemoveAllergy}
        />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Allergy sub-component (kept co-located — too small for its own file)
// ---------------------------------------------------------------------------

interface AllergyFieldProps {
  allergies: string[];
  inputValue: string;
  onInputChange: (value: string) => void;
  onAdd: () => void;
  onRemove: (allergy: string) => void;
}

function AllergyField({
  allergies,
  inputValue,
  onInputChange,
  onAdd,
  onRemove,
}: AllergyFieldProps) {
  return (
    <div className="rx-field">
      <Label>Alergias Conocidas</Label>
      <div className="rx-allergy-row">
        <Input
          value={inputValue}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onAdd()}
          placeholder="Agregar alergia"
        />
        <Button type="button" variant="outline" onClick={onAdd}>
          Agregar
        </Button>
      </div>
      {allergies.length > 0 && (
        <div className="rx-allergy-tags">
          {allergies.map((allergy) => (
            <span key={allergy} className="rx-allergy-tag">
              {allergy}
              <button
                type="button"
                onClick={() => onRemove(allergy)}
                className="rx-allergy-remove"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
