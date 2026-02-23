/**
 * DiagnosisTab Component
 *
 * Diagnosis, general instructions, and next appointment fields.
 * Single Responsibility: diagnosis data entry UI.
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 * @refactored 2026-02-22
 */

"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileText } from "lucide-react";

interface DiagnosisTabProps {
  diagnosis: string;
  diagnosisCode: string;
  generalInstructions: string;
  nextAppointment: string;
  onDiagnosisChange: (value: string) => void;
  onDiagnosisCodeChange: (value: string) => void;
  onGeneralInstructionsChange: (value: string) => void;
  onNextAppointmentChange: (value: string) => void;
}

export function DiagnosisTab({
  diagnosis,
  diagnosisCode,
  generalInstructions,
  nextAppointment,
  onDiagnosisChange,
  onDiagnosisCodeChange,
  onGeneralInstructionsChange,
  onNextAppointmentChange,
}: DiagnosisTabProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="rx-section-title">
          <FileText className="rx-section-icon" />
          Diagnóstico e Indicaciones
        </CardTitle>
      </CardHeader>
      <CardContent className="rx-field-group">
        <div className="rx-fields-3col">
          <div className="rx-field-wide">
            <Label htmlFor="diagnosis">
              Diagnóstico Principal <span className="rx-required">*</span>
            </Label>
            <textarea
              id="diagnosis"
              value={diagnosis}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                onDiagnosisChange(e.target.value)
              }
              placeholder="Ingrese el diagnóstico principal"
              rows={3}
              className="rx-textarea"
            />
          </div>
          <div className="rx-field">
            <Label htmlFor="diagnosis-code">Código CIE-10</Label>
            <Input
              id="diagnosis-code"
              value={diagnosisCode}
              onChange={(e) => onDiagnosisCodeChange(e.target.value)}
              placeholder="Ej: J06.9"
            />
          </div>
        </div>

        <div className="rx-field">
          <Label htmlFor="general-instructions">Indicaciones Generales</Label>
          <textarea
            id="general-instructions"
            value={generalInstructions}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
              onGeneralInstructionsChange(e.target.value)
            }
            placeholder="Indicaciones adicionales para el paciente (reposo, dieta, etc.)"
            rows={3}
            className="rx-textarea"
          />
        </div>

        <div className="rx-field">
          <Label htmlFor="next-appointment">Próxima Cita</Label>
          <Input
            id="next-appointment"
            value={nextAppointment}
            onChange={(e) => onNextAppointmentChange(e.target.value)}
            placeholder="Ej: En 2 semanas si persisten síntomas"
          />
        </div>
      </CardContent>
    </Card>
  );
}
