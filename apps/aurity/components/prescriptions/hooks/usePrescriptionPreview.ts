/**
 * usePrescriptionPreview Hook
 *
 * Derives a preview Prescription object from the current form state.
 * Follows SRP: presentation data derivation only.
 *
 * @author Bernard Uriza Orozco
 * @created 2026-02-22
 */

import { useMemo } from "react";
import type { Prescription } from "@/lib/api/prescriptions";
import type { PrescriptionFormState } from "../types";

/**
 * Builds a preview prescription from form state, falling back
 * to the persisted prescription when available.
 */
export function usePrescriptionPreview(
  state: PrescriptionFormState,
  sessionId?: string,
): Prescription | null {
  const {
    createdPrescription,
    patient,
    physician,
    diagnosis,
    diagnosisCode,
    medications,
    generalInstructions,
    nextAppointment,
  } = state;

  return useMemo(() => {
    if (createdPrescription) return createdPrescription;

    const hasMinimumData =
      medications.length > 0 &&
      patient.name.trim() !== "" &&
      physician.name.trim() !== "" &&
      diagnosis.trim() !== "";

    if (!hasMinimumData) return null;

    return {
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
    } satisfies Prescription;
  }, [
    createdPrescription,
    patient,
    physician,
    diagnosis,
    diagnosisCode,
    medications,
    generalInstructions,
    nextAppointment,
    sessionId,
  ]);
}
