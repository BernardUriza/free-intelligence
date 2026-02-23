/**
 * usePrescriptionForm Hook
 *
 * Encapsulates all state management, validation, and side-effects
 * for the prescription form. Follows SRP: manages form state only.
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 * @refactored 2026-02-22
 */

"use client";

import { useState, useCallback } from "react";
import type {
  Medication,
  PatientInfo,
  PhysicianInfo,
  Prescription,
} from "@/lib/api/prescriptions";
import { createPrescription, signPrescription } from "@/lib/api/prescriptions";
import { toastSuccess, toastError } from "@/lib/swal";
import type {
  PrescriptionFormProps,
  PrescriptionFormState,
  PrescriptionFormHandlers,
  PrescriptionTab,
} from "../types";

// ---------------------------------------------------------------------------
// Initial state builders
// ---------------------------------------------------------------------------

function buildInitialPatient(
  initial?: Partial<PatientInfo>,
): PatientInfo {
  return {
    name: initial?.name ?? "",
    age: initial?.age ?? "",
    weight_kg: initial?.weight_kg,
    allergies: initial?.allergies ?? [],
    ...initial,
  };
}

function buildInitialPhysician(
  initial?: Partial<PhysicianInfo>,
): PhysicianInfo {
  return {
    name: initial?.name ?? "",
    professional_license: initial?.professional_license ?? "",
    specialty: initial?.specialty ?? "",
    institution: initial?.institution ?? "",
    ...initial,
  };
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

function validatePrescription(
  patient: PatientInfo,
  physician: PhysicianInfo,
  diagnosis: string,
  medications: Medication[],
): string[] {
  const errors: string[] = [];

  if (!patient.name.trim()) errors.push("Nombre del paciente requerido");
  if (!physician.name.trim()) errors.push("Nombre del médico requerido");
  if (!physician.professional_license.trim())
    errors.push("Cédula profesional requerida");
  if (!diagnosis.trim()) errors.push("Diagnóstico requerido");
  if (medications.length === 0) errors.push("Agregue al menos un medicamento");

  return errors;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function usePrescriptionForm(props: PrescriptionFormProps) {
  const {
    sessionId,
    initialPatient,
    initialPhysician,
    initialDiagnosis,
    onComplete,
  } = props;

  // --- Core form state ---
  const [patient, setPatient] = useState<PatientInfo>(
    () => buildInitialPatient(initialPatient),
  );
  const [physician, setPhysician] = useState<PhysicianInfo>(
    () => buildInitialPhysician(initialPhysician),
  );
  const [diagnosis, setDiagnosis] = useState(initialDiagnosis ?? "");
  const [diagnosisCode, setDiagnosisCode] = useState("");
  const [medications, setMedications] = useState<Medication[]>([]);
  const [generalInstructions, setGeneralInstructions] = useState("");
  const [nextAppointment, setNextAppointment] = useState("");

  // --- UI state ---
  const [activeTab, setActiveTabInternal] = useState<PrescriptionTab>("patient");
  const setActiveTab = useCallback(
    (tab: string) => setActiveTabInternal(tab as PrescriptionTab),
    [],
  );
  const [editingMedIndex, setEditingMedIndex] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdPrescription, setCreatedPrescription] =
    useState<Prescription | null>(null);
  const [allergyInput, setAllergyInput] = useState("");

  // --- Medication handlers ---
  const handleAddMedication = useCallback(
    (med: Medication) => {
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
    },
    [editingMedIndex],
  );

  const handleEditMedication = useCallback((index: number) => {
    setEditingMedIndex(index);
  }, []);

  const handleRemoveMedication = useCallback(
    (index: number) => {
      setMedications((prev) => prev.filter((_, i) => i !== index));
      if (editingMedIndex === index) setEditingMedIndex(null);
    },
    [editingMedIndex],
  );

  const handleCancelEditMedication = useCallback(() => {
    setEditingMedIndex(null);
  }, []);

  // --- Allergy handlers ---
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

  // --- Submit / Sign / Print ---
  const handleSubmit = useCallback(async () => {
    const errors = validatePrescription(
      patient,
      physician,
      diagnosis,
      medications,
    );
    if (errors.length > 0) {
      toastError("Corrija los siguientes errores: " + errors.join(", "));
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await createPrescription({
        template_id: "default",
        session_id: sessionId,
        patient,
        physician,
        diagnosis,
        diagnosis_code: diagnosisCode || undefined,
        medications,
        general_instructions: generalInstructions || undefined,
        next_appointment: nextAppointment || undefined,
      });

      if (response.success && response.prescription) {
        setCreatedPrescription(response.prescription);
        toastSuccess("Receta creada exitosamente");
        setActiveTab("preview");
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Error desconocido";
      toastError(`Error al crear la receta: ${message}`);
    } finally {
      setIsSubmitting(false);
    }
  }, [
    patient,
    physician,
    diagnosis,
    diagnosisCode,
    medications,
    generalInstructions,
    nextAppointment,
    sessionId,
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
      const message =
        error instanceof Error ? error.message : "Error desconocido";
      toastError(`Error al firmar la receta: ${message}`);
    } finally {
      setIsSubmitting(false);
    }
  }, [createdPrescription, onComplete]);

  const handlePrint = useCallback(() => {
    window.print();
  }, []);

  // --- Return typed state + handlers ---
  const state: PrescriptionFormState = {
    patient,
    physician,
    diagnosis,
    diagnosisCode,
    medications,
    generalInstructions,
    nextAppointment,
    activeTab,
    editingMedIndex,
    isSubmitting,
    createdPrescription,
    allergyInput,
  };

  const handlers: PrescriptionFormHandlers = {
    setPatient,
    setPhysician,
    setDiagnosis,
    setDiagnosisCode,
    setGeneralInstructions,
    setNextAppointment,
    setActiveTab,
    setAllergyInput,
    handleAddMedication,
    handleEditMedication,
    handleRemoveMedication,
    handleCancelEditMedication,
    handleAddAllergy,
    handleRemoveAllergy,
    handleSubmit,
    handleSign,
    handlePrint,
  };

  return { state, handlers } as const;
}
