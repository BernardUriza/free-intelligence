/**
 * usePatientSearch Hook
 *
 * Manages patient search with debounce, dropdown state, and inline creation.
 * Uses shared validation from PatientFormFields.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchPatients, createPatient, type Patient } from '@/lib/api/patients';
import {
  usePatientFormValidation,
  validatePatientForm,
  type PatientFormData,
  type PatientFormField,
} from '@/components/patients/usePatientFormValidation';

interface UsePatientSearchProps {
  onPatientSelect: (patientId: string, patientName: string) => void;
}

export function usePatientSearch({ onPatientSelect }: UsePatientSearchProps) {
  const dropdownRef = useRef<HTMLDivElement>(null!);
  const [search, setSearch] = useState('');
  const [results, setResults] = useState<Patient[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newPatient, setNewPatient] = useState<PatientFormData>({
    nombre: '',
    apellido: '',
    fecha_nacimiento: '',
  });
  const [creating, setCreating] = useState(false);

  // Use shared validation hook
  const validation = usePatientFormValidation();

  // Search patients with debounce
  useEffect(() => {
    if (search.length < 2) {
      setResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await fetchPatients({ search, limit: 10 });
        setResults(data);
        setShowDropdown(true);
      } catch (err) {
        console.error('Failed to search patients:', err);
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [search]);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };

    if (showDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showDropdown]);

  const handleSelectPatient = useCallback((patient: Patient) => {
    onPatientSelect(patient.id, patient.name);
    setSearch(patient.name);
    setShowDropdown(false);
  }, [onPatientSelect]);

  /**
   * Handle field change with immediate error clear
   */
  const handleNewPatientChange = useCallback((field: PatientFormField, value: string) => {
    setNewPatient((prev) => ({ ...prev, [field]: value }));
    validation.clearFieldError(field);
  }, [validation]);

  /**
   * Handle field blur
   */
  const handleFieldBlur = useCallback((field: PatientFormField) => {
    validation.handleBlur(field, newPatient[field]);
  }, [validation, newPatient]);

  const handleCreatePatient = useCallback(async () => {
    // Full form validation
    const { isValid } = validation.validate(newPatient);
    
    if (!isValid) {
      return;
    }

    setCreating(true);
    try {
      const created = await createPatient({
        nombre: newPatient.nombre,
        apellido: newPatient.apellido,
        fecha_nacimiento: newPatient.fecha_nacimiento,
      });

      onPatientSelect(created.id, created.name);
      setSearch(created.name);
      setShowCreateForm(false);
      setShowDropdown(false);
      setNewPatient({ nombre: '', apellido: '', fecha_nacimiento: '' });
      validation.reset();
    } catch (err) {
      console.error('Failed to create patient:', err);
      alert('Error al crear paciente');
    } finally {
      setCreating(false);
    }
  }, [newPatient, onPatientSelect]);

  const openCreateForm = useCallback(() => {
    setShowCreateForm(true);
    setShowDropdown(false);
  }, []);

  const closeCreateForm = useCallback(() => {
    setShowCreateForm(false);
    setNewPatient({ nombre: '', apellido: '', fecha_nacimiento: '' });
    validation.reset();
  }, [validation]);

  const clearSearch = useCallback(() => {
    setSearch('');
    setResults([]);
    setShowDropdown(false);
  }, []);

  const handleFocus = useCallback(() => {
    if (results.length > 0) {
      setShowDropdown(true);
    }
  }, [results.length]);

  return {
    dropdownRef,
    search,
    setSearch,
    results,
    showDropdown,
    loading,
    showCreateForm,
    newPatient,
    handleNewPatientChange,
    creating,
    handleSelectPatient,
    handleCreatePatient,
    openCreateForm,
    closeCreateForm,
    clearSearch,
    handleFocus,
    // Validation from shared hook
    getFieldError: validation.getFieldError,
    handleFieldBlur,
  };
}
