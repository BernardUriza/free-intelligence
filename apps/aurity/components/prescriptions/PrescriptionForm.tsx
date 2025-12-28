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
import { Textarea } from "@/components/ui/textarea";
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
import { toast } from "sonner";

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
      toast.error("Corrija los siguientes errores:", {
        description: errors.join(", "),
      });
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
        toast.success("Receta creada exitosamente");
        setActiveTab("preview");
      }
    } catch (error) {
      toast.error("Error al crear la receta", {
        description: error instanceof Error ? error.message : "Error desconocido",
      });
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
        toast.success("Receta firmada exitosamente");
        onComplete?.(response.prescription);
      }
    } catch (error) {
      toast.error("Error al firmar la receta", {
        description: error instanceof Error ? error.message : "Error desconocido",
      });
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
    <div className="max-w-4xl mx-auto">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5 mb-6">
          <TabsTrigger value="patient" className="flex items-center gap-1.5">
            <User className="w-4 h-4" />
            <span className="hidden sm:inline">Paciente</span>
          </TabsTrigger>
          <TabsTrigger value="physician" className="flex items-center gap-1.5">
            <Stethoscope className="w-4 h-4" />
            <span className="hidden sm:inline">Médico</span>
          </TabsTrigger>
          <TabsTrigger value="diagnosis" className="flex items-center gap-1.5">
            <FileText className="w-4 h-4" />
            <span className="hidden sm:inline">Diagnóstico</span>
          </TabsTrigger>
          <TabsTrigger value="medications" className="flex items-center gap-1.5">
            <Pill className="w-4 h-4" />
            <span className="hidden sm:inline">Medicamentos</span>
            {medications.length > 0 && (
              <span className="ml-1 px-1.5 py-0.5 text-xs bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 rounded-full">
                {medications.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="preview" className="flex items-center gap-1.5">
            <Eye className="w-4 h-4" />
            <span className="hidden sm:inline">Vista Previa</span>
          </TabsTrigger>
        </TabsList>

        {/* Patient Tab */}
        <TabsContent value="patient">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="w-5 h-5" />
                Información del Paciente
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="patient-name">
                    Nombre Completo <span className="text-red-500">*</span>
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
                <div className="space-y-2">
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
                <div className="space-y-2">
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
                <div className="space-y-2">
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
              <div className="space-y-2">
                <Label>Alergias Conocidas</Label>
                <div className="flex gap-2">
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
                  <div className="flex flex-wrap gap-2 mt-2">
                    {patient.allergies.map((allergy) => (
                      <span
                        key={allergy}
                        className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-full text-sm"
                      >
                        {allergy}
                        <button
                          type="button"
                          onClick={() => handleRemoveAllergy(allergy)}
                          className="hover:text-red-900 dark:hover:text-red-100"
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
              <CardTitle className="flex items-center gap-2">
                <Stethoscope className="w-5 h-5" />
                Información del Médico
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="physician-name">
                    Nombre Completo <span className="text-red-500">*</span>
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
                <div className="space-y-2">
                  <Label htmlFor="physician-license">
                    Cédula Profesional <span className="text-red-500">*</span>
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
                <div className="space-y-2">
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
                <div className="space-y-2">
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
                <div className="space-y-2 md:col-span-2">
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
                <div className="space-y-2 md:col-span-2">
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
                <div className="space-y-2">
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
                <div className="space-y-2">
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
              <CardTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Diagnóstico e Indicaciones
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="diagnosis">
                    Diagnóstico Principal <span className="text-red-500">*</span>
                  </Label>
                  <Textarea
                    id="diagnosis"
                    value={diagnosis}
                    onChange={(e) => setDiagnosis(e.target.value)}
                    placeholder="Ingrese el diagnóstico principal"
                    rows={3}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="diagnosis-code">Código CIE-10</Label>
                  <Input
                    id="diagnosis-code"
                    value={diagnosisCode}
                    onChange={(e) => setDiagnosisCode(e.target.value)}
                    placeholder="Ej: J06.9"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="general-instructions">
                  Indicaciones Generales
                </Label>
                <Textarea
                  id="general-instructions"
                  value={generalInstructions}
                  onChange={(e) => setGeneralInstructions(e.target.value)}
                  placeholder="Indicaciones adicionales para el paciente (reposo, dieta, etc.)"
                  rows={3}
                />
              </div>

              <div className="space-y-2">
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
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Pill className="w-5 h-5" />
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
          <div className="space-y-4">
            {previewPrescription ? (
              <>
                <div className="flex justify-between items-center mb-4">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-500">Estado:</span>
                    <PrescriptionStatusBadge
                      status={previewPrescription.status}
                    />
                  </div>
                  <div className="flex gap-2">
                    {!createdPrescription && (
                      <Button
                        onClick={handleSubmit}
                        disabled={isSubmitting}
                        variant="default"
                      >
                        <Save className="w-4 h-4 mr-1.5" />
                        Guardar Receta
                      </Button>
                    )}
                    {createdPrescription &&
                      createdPrescription.status === "draft" && (
                        <Button
                          onClick={handleSign}
                          disabled={isSubmitting}
                          variant="default"
                        >
                          <Signature className="w-4 h-4 mr-1.5" />
                          Firmar Receta
                        </Button>
                      )}
                    {createdPrescription && (
                      <Button
                        onClick={handlePrint}
                        variant="outline"
                        className="print:hidden"
                      >
                        <Printer className="w-4 h-4 mr-1.5" />
                        Imprimir
                      </Button>
                    )}
                  </div>
                </div>

                <div className="border rounded-lg overflow-hidden shadow-lg print:shadow-none print:border-0">
                  <PrescriptionPreview prescription={previewPrescription} />
                </div>
              </>
            ) : (
              <Card>
                <CardContent className="py-12 text-center text-slate-500">
                  <AlertCircle className="w-12 h-12 mx-auto mb-4 opacity-30" />
                  <p>Complete la información para ver la vista previa</p>
                  <p className="text-sm mt-2">
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
