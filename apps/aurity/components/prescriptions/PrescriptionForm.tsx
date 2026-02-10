/**
 * PrescriptionForm Component
 *
 * Main form for creating and editing prescriptions.
 * Integrates patient info, diagnosis, and medications.
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 */

"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
// Note: Using native textarea - no custom Textarea component exists
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MedicationForm } from "./MedicationForm";
import { MedicationList } from "./MedicationList";
import { PrescriptionPreview } from "./PrescriptionPreview";
import { PrescriptionStatusBadge } from "./PrescriptionStatusBadge";
import {
  Medication,
  PatientInfo,
  PhysicianInfo,
  Prescription,
  CreatePrescriptionRequest,
  createPrescription,
  signPrescription,
} from "@/lib/api/prescriptions";
import {
  User,
  Stethoscope,
  FileText,
  Pill,
  Eye,
  Save,
  Signature,
  Printer,
  AlertCircle,
} from "lucide-react";
import { toastSuccess, toastError } from "@/lib/swal";

interface PrescriptionFormProps {
  sessionId?: string;
  initialPatient?: Partial<PatientInfo>;
  initialPhysician?: Partial<PhysicianInfo>;
  initialDiagnosis?: string;
  onComplete?: (prescription: Prescription) => void;
}

export function PrescriptionForm({
  sessionId,
  initialPatient,
  initialPhysician,
  initialDiagnosis,
  onComplete,
}: PrescriptionFormProps) {
  // Form state
  const [patient, setPatient] = useState<PatientInfo>({
    name: initialPatient?.name || "",
    age: initialPatient?.age || "",
    weight_kg: initialPatient?.weight_kg,
    allergies: initialPatient?.allergies || [],
    ...initialPatient,
  });

  const [physician, setPhysician] = useState<PhysicianInfo>({
    name: initialPhysician?.name || "",
    professional_license: initialPhysician?.professional_license || "",
    specialty: initialPhysician?.specialty || "",
    institution: initialPhysician?.institution || "",
    ...initialPhysician,
  });

  const [diagnosis, setDiagnosis] = useState(initialDiagnosis || "");
  const [diagnosisCode, setDiagnosisCode] = useState("");
  const [medications, setMedications] = useState<Medication[]>([]);
  const [generalInstructions, setGeneralInstructions] = useState("");
  const [nextAppointment, setNextAppointment] = useState("");

  // UI state
  const [activeTab, setActiveTab] = useState("patient");
  const [editingMedIndex, setEditingMedIndex] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdPrescription, setCreatedPrescription] =
    useState<Prescription | null>(null);

  // Allergy input
  const [allergyInput, setAllergyInput] = useState("");

  // Handlers
  const handleAddMedication = useCallback((med: Medication) => {
    if (editingMedIndex !== null) {
      setMedications((prev) => {
        const updated = [...prev];
        updated[editingMedIndex] = med;
        return updated;
      });
      setEditingMedIndex(null);
    } else {
      setMedications((prev) => [...prev, med]);
    }
  }, [editingMedIndex]);

  const handleEditMedication = useCallback((index: number) => {
    setEditingMedIndex(index);
  }, []);

  const handleRemoveMedication = useCallback((index: number) => {
    setMedications((prev) => prev.filter((_, i) => i !== index));
    if (editingMedIndex === index) {
      setEditingMedIndex(null);
    }
  }, [editingMedIndex]);

  const handleAddAllergy = useCallback(() => {
    const trimmed = allergyInput.trim();
    if (trimmed && !patient.allergies.includes(trimmed)) {
      setPatient((prev) => ({
        ...prev,
        allergies: [...prev.allergies, trimmed],
      }));
      setAllergyInput("");
    }
  }, [allergyInput, patient.allergies]);

  const handleRemoveAllergy = useCallback((allergy: string) => {
    setPatient((prev) => ({
      ...prev,
      allergies: prev.allergies.filter((a) => a !== allergy),
    }));
  }, []);

  const validateForm = useCallback((): string[] => {
    const errors: string[] = [];

    if (!patient.name.trim()) errors.push("Nombre del paciente requerido");
    if (!physician.name.trim()) errors.push("Nombre del médico requerido");
    if (!physician.professional_license.trim())
      errors.push("Cédula profesional requerida");
    if (!diagnosis.trim()) errors.push("Diagnóstico requerido");
    if (medications.length === 0)
      errors.push("Agregue al menos un medicamento");

    return errors;
  }, [patient, physician, diagnosis, medications]);

  const handleSubmit = useCallback(async () => {
    const errors = validateForm();
    if (errors.length > 0) {
      toastError("Corrija los siguientes errores: " + errors.join(", "));
      return;
    }

    setIsSubmitting(true);

    try {
      const request: CreatePrescriptionRequest = {
        template_id: "default",
        session_id: sessionId,
        patient,
        physician,
        diagnosis,
        diagnosis_code: diagnosisCode || undefined,
        medications,
        general_instructions: generalInstructions || undefined,
        next_appointment: nextAppointment || undefined,
      };

      const response = await createPrescription(request);

      if (response.success && response.prescription) {
        setCreatedPrescription(response.prescription);
        toastSuccess("Receta creada exitosamente");
        setActiveTab("preview");
      }
    } catch (error) {
      toastError("Error al crear la receta: " + (error instanceof Error ? error.message : "Error desconocido"));
    } finally {
      setIsSubmitting(false);
    }
  }, [
    validateForm,
    sessionId,
    patient,
    physician,
    diagnosis,
    diagnosisCode,
    medications,
    generalInstructions,
    nextAppointment,
  ]);

  const handleSign = useCallback(async () => {
    if (!createdPrescription) return;

    setIsSubmitting(true);

    try {
      const response = await signPrescription(createdPrescription.id);

      if (response.success && response.prescription) {
        setCreatedPrescription(response.prescription);
        toastSuccess("Receta firmada exitosamente");
        onComplete?.(response.prescription);
      }
    } catch (error) {
      toastError("Error al firmar la receta: " + (error instanceof Error ? error.message : "Error desconocido"));
    } finally {
      setIsSubmitting(false);
    }
  }, [createdPrescription, onComplete]);

  const handlePrint = useCallback(() => {
    window.print();
  }, []);

  // Build preview prescription object for display
  const previewPrescription: Prescription | null = createdPrescription || (
    medications.length > 0 && patient.name && physician.name && diagnosis
      ? {
          id: "preview",
          template_id: "default",
          session_id: sessionId,
          status: "draft",
          patient,
          physician,
          diagnosis,
          diagnosis_code: diagnosisCode,
          secondary_diagnoses: [],
          medications,
          general_instructions: generalInstructions,
          next_appointment: nextAppointment,
          validity_days: 30,
          created_at: new Date().toISOString(),
          custom_fields: {},
          medication_count: medications.length,
          is_signed: false,
          is_valid: true,
        }
      : null
  );

  return (
    <div className="rx-form-container">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
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
            {medications.length > 0 && (
              <span className="rx-tab-count">
                {medications.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="preview" className="rx-tab-trigger">
            <Eye className="rx-tab-icon" />
            <span className="rx-tab-label">Vista Previa</span>
          </TabsTrigger>
        </TabsList>

        {/* Patient Tab */}
        <TabsContent value="patient">
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
                      setPatient((p) => ({ ...p, name: e.target.value }))
                    }
                    placeholder="Nombre del paciente"
                  />
                </div>
                <div className="rx-field">
                  <Label htmlFor="patient-age">Edad</Label>
                  <Input
                    id="patient-age"
                    value={patient.age || ""}
                    onChange={(e) =>
                      setPatient((p) => ({ ...p, age: e.target.value }))
                    }
                    placeholder="Ej: 45 años"
                  />
                </div>
                <div className="rx-field">
                  <Label htmlFor="patient-weight">Peso (kg)</Label>
                  <Input
                    id="patient-weight"
                    type="number"
                    value={patient.weight_kg || ""}
                    onChange={(e) =>
                      setPatient((p) => ({
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
                    value={patient.gender || ""}
                    onChange={(e) =>
                      setPatient((p) => ({ ...p, gender: e.target.value }))
                    }
                    placeholder="Ej: Femenino"
                  />
                </div>
              </div>

              {/* Allergies */}
              <div className="rx-field">
                <Label>Alergias Conocidas</Label>
                <div className="rx-allergy-row">
                  <Input
                    value={allergyInput}
                    onChange={(e) => setAllergyInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAddAllergy()}
                    placeholder="Agregar alergia"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleAddAllergy}
                  >
                    Agregar
                  </Button>
                </div>
                {patient.allergies.length > 0 && (
                  <div className="rx-allergy-tags">
                    {patient.allergies.map((allergy) => (
                      <span
                        key={allergy}
                        className="rx-allergy-tag"
                      >
                        {allergy}
                        <button
                          type="button"
                          onClick={() => handleRemoveAllergy(allergy)}
                          className="rx-allergy-remove"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Physician Tab */}
        <TabsContent value="physician">
          <Card>
            <CardHeader>
              <CardTitle className="rx-section-title">
                <Stethoscope className="rx-section-icon" />
                Información del Médico
              </CardTitle>
            </CardHeader>
            <CardContent className="rx-field-group">
              <div className="rx-fields-2col">
                <div className="rx-field">
                  <Label htmlFor="physician-name">
                    Nombre Completo <span className="rx-required">*</span>
                  </Label>
                  <Input
                    id="physician-name"
                    value={physician.name}
                    onChange={(e) =>
                      setPhysician((p) => ({ ...p, name: e.target.value }))
                    }
                    placeholder="Dr(a). Nombre Completo"
                  />
                </div>
                <div className="rx-field">
                  <Label htmlFor="physician-license">
                    Cédula Profesional <span className="rx-required">*</span>
                  </Label>
                  <Input
                    id="physician-license"
                    value={physician.professional_license}
                    onChange={(e) =>
                      setPhysician((p) => ({
                        ...p,
                        professional_license: e.target.value,
                      }))
                    }
                    placeholder="Número de cédula"
                  />
                </div>
                <div className="rx-field">
                  <Label htmlFor="physician-specialty">Especialidad</Label>
                  <Input
                    id="physician-specialty"
                    value={physician.specialty || ""}
                    onChange={(e) =>
                      setPhysician((p) => ({ ...p, specialty: e.target.value }))
                    }
                    placeholder="Ej: Medicina General"
                  />
                </div>
                <div className="rx-field">
                  <Label htmlFor="physician-specialty-license">
                    Cédula de Especialidad
                  </Label>
                  <Input
                    id="physician-specialty-license"
                    value={physician.specialty_license || ""}
                    onChange={(e) =>
                      setPhysician((p) => ({
                        ...p,
                        specialty_license: e.target.value,
                      }))
                    }
                    placeholder="Número de cédula de especialidad"
                  />
                </div>
                <div className="rx-field-wide">
                  <Label htmlFor="physician-institution">
                    Institución / Consultorio
                  </Label>
                  <Input
                    id="physician-institution"
                    value={physician.institution || ""}
                    onChange={(e) =>
                      setPhysician((p) => ({
                        ...p,
                        institution: e.target.value,
                      }))
                    }
                    placeholder="Nombre del consultorio o institución"
                  />
                </div>
                <div className="rx-field-wide">
                  <Label htmlFor="physician-address">Dirección</Label>
                  <Input
                    id="physician-address"
                    value={physician.address || ""}
                    onChange={(e) =>
                      setPhysician((p) => ({ ...p, address: e.target.value }))
                    }
                    placeholder="Dirección del consultorio"
                  />
                </div>
                <div className="rx-field">
                  <Label htmlFor="physician-phone">Teléfono</Label>
                  <Input
                    id="physician-phone"
                    value={physician.phone || ""}
                    onChange={(e) =>
                      setPhysician((p) => ({ ...p, phone: e.target.value }))
                    }
                    placeholder="Teléfono de contacto"
                  />
                </div>
                <div className="rx-field">
                  <Label htmlFor="physician-email">Email</Label>
                  <Input
                    id="physician-email"
                    type="email"
                    value={physician.email || ""}
                    onChange={(e) =>
                      setPhysician((p) => ({ ...p, email: e.target.value }))
                    }
                    placeholder="correo@ejemplo.com"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Diagnosis Tab */}
        <TabsContent value="diagnosis">
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
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDiagnosis(e.target.value)}
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
                    onChange={(e) => setDiagnosisCode(e.target.value)}
                    placeholder="Ej: J06.9"
                  />
                </div>
              </div>

              <div className="rx-field">
                <Label htmlFor="general-instructions">
                  Indicaciones Generales
                </Label>
                <textarea
                  id="general-instructions"
                  value={generalInstructions}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setGeneralInstructions(e.target.value)}
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
                  onChange={(e) => setNextAppointment(e.target.value)}
                  placeholder="Ej: En 2 semanas si persisten síntomas"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Medications Tab */}
        <TabsContent value="medications">
          <div className="rx-med-stack">
            <Card>
              <CardHeader>
                <CardTitle className="rx-section-title">
                  <Pill className="rx-section-icon" />
                  {editingMedIndex !== null
                    ? `Editando Medicamento ${editingMedIndex + 1}`
                    : "Agregar Medicamento"}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <MedicationForm
                  medication={
                    editingMedIndex !== null
                      ? medications[editingMedIndex]
                      : undefined
                  }
                  onSave={handleAddMedication}
                  onCancel={
                    editingMedIndex !== null
                      ? () => setEditingMedIndex(null)
                      : undefined
                  }
                  isEditing={editingMedIndex !== null}
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
                  onEdit={handleEditMedication}
                  onRemove={handleRemoveMedication}
                />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Preview Tab */}
        <TabsContent value="preview">
          <div className="rx-preview-stack">
            {previewPrescription ? (
              <>
                <div className="rx-preview-toolbar">
                  <div className="rx-preview-status">
                    <span className="rx-preview-status-label">Estado:</span>
                    <PrescriptionStatusBadge
                      status={previewPrescription.status}
                    />
                  </div>
                  <div className="rx-preview-actions">
                    {!createdPrescription && (
                      <Button
                        onClick={handleSubmit}
                        disabled={isSubmitting}
                        variant="primary"
                      >
                        <Save className="rx-btn-icon" />
                        Guardar Receta
                      </Button>
                    )}
                    {createdPrescription &&
                      createdPrescription.status === "draft" && (
                        <Button
                          onClick={handleSign}
                          disabled={isSubmitting}
                          variant="primary"
                        >
                          <Signature className="rx-btn-icon" />
                          Firmar Receta
                        </Button>
                      )}
                    {createdPrescription && (
                      <Button
                        onClick={handlePrint}
                        variant="outline"
                        className="rx-print-hidden"
                      >
                        <Printer className="rx-btn-icon" />
                        Imprimir
                      </Button>
                    )}
                  </div>
                </div>

                <div className="rx-preview-frame">
                  <PrescriptionPreview prescription={previewPrescription} />
                </div>
              </>
            ) : (
              <Card>
                <CardContent className="rx-empty-content">
                  <AlertCircle className="rx-empty-icon" />
                  <p>Complete la información para ver la vista previa</p>
                  <p className="rx-empty-hint">
                    Se requiere: paciente, médico, diagnóstico y al menos un
                    medicamento
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
