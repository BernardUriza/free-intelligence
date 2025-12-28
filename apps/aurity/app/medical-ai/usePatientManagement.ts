/**
 * usePatientManagement - Patient state management hook
 *
 * Handles patient list, creation, editing, and selection
 */

import { useState, useEffect } from 'react';
import { Patient } from '@aurity-standalone/types/patient';
import { Patient as MedicalPatient } from '@aurity-standalone/types/medical';
import { fetchPatients } from '@/lib/api/patients';

export function usePatientManagement() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loadingPatients, setLoadingPatients] = useState(false);
  const [patientsError, setPatientsError] = useState<string | null>(null);
  const [showPatientModal, setShowPatientModal] = useState(false);
  const [editingPatient, setEditingPatient] = useState<Patient | null>(null);
  const [selectedPatient, setSelectedPatient] = useState<MedicalPatient | null>(null);

  // Load patients on mount
  useEffect(() => {
    async function loadPatients() {
      try {
        setLoadingPatients(true);
        setPatientsError(null);
        const fetchedPatients = await fetchPatients({ limit: 100 });
        setPatients(fetchedPatients);
      } catch (err) {
        console.error('Failed to load patients:', err);
        setPatientsError(err instanceof Error ? err.message : 'Error al cargar pacientes');
      } finally {
        setLoadingPatients(false);
      }
    }

    loadPatients();
  }, []);

  // Convert Patient to MedicalPatient format
  const handleStartNewConsultation = (patient: Patient): MedicalPatient => {
    const medicalPatient: MedicalPatient = {
      id: patient.id,
      name: patient.name,
      age: patient.age,
      gender: patient.gender,
      medicalHistory: patient.medicalHistory || [],
      allergies: patient.allergies || [],
      chronicConditions: patient.chronicConditions || [],
      currentMedications: patient.currentMedications || [],
    };
    setSelectedPatient(medicalPatient);
    return medicalPatient;
  };

  const handleEditPatient = (patient: Patient) => {
    setEditingPatient(patient);
  };

  return {
    patients,
    loadingPatients,
    patientsError,
    showPatientModal,
    setShowPatientModal,
    editingPatient,
    setEditingPatient,
    selectedPatient,
    setSelectedPatient,
    handleStartNewConsultation,
    handleEditPatient,
  };
}
