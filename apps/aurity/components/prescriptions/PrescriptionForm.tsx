/**
 * PrescriptionForm Component
 *
 * Composition root that wires hooks to tab-panel components.
 * All state lives in usePrescriptionForm; each tab is a separate component.
 *
 * SOLID principles applied:
 *  - SRP: state in hook, presentation in tab components, types in types.ts
 *  - OCP: new tabs can be added without modifying existing ones
 *  - ISP: each tab receives only the props it needs
 *  - DIP: depends on abstractions (handler interfaces) not concretions
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 * @refactored 2026-02-22
 */

"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { User, Stethoscope, FileText, Pill, Eye } from "lucide-react";

import type { PrescriptionFormProps } from "./types";
import { usePrescriptionForm } from "./hooks/usePrescriptionForm";
import { usePrescriptionPreview } from "./hooks/usePrescriptionPreview";
import { PatientTab } from "./tabs/PatientTab";
import { PhysicianTab } from "./tabs/PhysicianTab";
import { DiagnosisTab } from "./tabs/DiagnosisTab";
import { MedicationsTab } from "./tabs/MedicationsTab";
import { PreviewTab } from "./tabs/PreviewTab";

export function PrescriptionForm(props: PrescriptionFormProps) {
  const { state, handlers } = usePrescriptionForm(props);
  const previewPrescription = usePrescriptionPreview(state, props.sessionId);

  return (
    <div className="rx-form-container">
      <Tabs value={state.activeTab} onValueChange={handlers.setActiveTab}>
        <TabsList className="rx-tab-grid">
          <TabsTrigger value="patient" className="rx-tab-trigger">
            <User className="rx-tab-icon" />
            <span className="rx-tab-label">Paciente</span>
          </TabsTrigger>
          <TabsTrigger value="physician" className="rx-tab-trigger">
            <Stethoscope className="rx-tab-icon" />
            <span className="rx-tab-label">Médico</span>
          </TabsTrigger>
          <TabsTrigger value="diagnosis" className="rx-tab-trigger">
            <FileText className="rx-tab-icon" />
            <span className="rx-tab-label">Diagnóstico</span>
          </TabsTrigger>
          <TabsTrigger value="medications" className="rx-tab-trigger">
            <Pill className="rx-tab-icon" />
            <span className="rx-tab-label">Medicamentos</span>
            {state.medications.length > 0 && (
              <span className="rx-tab-count">{state.medications.length}</span>
            )}
          </TabsTrigger>
          <TabsTrigger value="preview" className="rx-tab-trigger">
            <Eye className="rx-tab-icon" />
            <span className="rx-tab-label">Vista Previa</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="patient">
          <PatientTab
            patient={state.patient}
            allergyInput={state.allergyInput}
            onPatientChange={handlers.setPatient}
            onAllergyInputChange={handlers.setAllergyInput}
            onAddAllergy={handlers.handleAddAllergy}
            onRemoveAllergy={handlers.handleRemoveAllergy}
          />
        </TabsContent>

        <TabsContent value="physician">
          <PhysicianTab
            physician={state.physician}
            onPhysicianChange={handlers.setPhysician}
          />
        </TabsContent>

        <TabsContent value="diagnosis">
          <DiagnosisTab
            diagnosis={state.diagnosis}
            diagnosisCode={state.diagnosisCode}
            generalInstructions={state.generalInstructions}
            nextAppointment={state.nextAppointment}
            onDiagnosisChange={handlers.setDiagnosis}
            onDiagnosisCodeChange={handlers.setDiagnosisCode}
            onGeneralInstructionsChange={handlers.setGeneralInstructions}
            onNextAppointmentChange={handlers.setNextAppointment}
          />
        </TabsContent>

        <TabsContent value="medications">
          <MedicationsTab
            medications={state.medications}
            editingMedIndex={state.editingMedIndex}
            onAddMedication={handlers.handleAddMedication}
            onEditMedication={handlers.handleEditMedication}
            onRemoveMedication={handlers.handleRemoveMedication}
            onCancelEdit={handlers.handleCancelEditMedication}
          />
        </TabsContent>

        <TabsContent value="preview">
          <PreviewTab
            previewPrescription={previewPrescription}
            createdPrescription={state.createdPrescription}
            isSubmitting={state.isSubmitting}
            onSubmit={handlers.handleSubmit}
            onSign={handlers.handleSign}
            onPrint={handlers.handlePrint}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
