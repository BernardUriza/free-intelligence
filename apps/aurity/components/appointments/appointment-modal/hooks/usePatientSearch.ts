/**
 * usePatientSearch Hook
 *
 * Manages patient search with debounce, dropdown state, and inline creation.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchPatients, createPatient, type Patient } from '@/lib/api/patients';
import type { NewPatientForm } from '../types';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('PatientSearch');

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
  const [newPatient, setNewPatient] = useState<NewPatientForm>({
    nombre: '',
    apellido: '',
    email: '',
    phone: '',
  });
  const [creating, setCreating] = useState(false);

  // Search patients with debounce
  useEffect(() => {
    if (search.length < 2) {
      setResults([]);
      return;
    }

    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await fetchPatients({ search, limit: 10 }, { signal: controller.signal });
        if (!controller.signal.aborted) {
          setResults(data);
          setShowDropdown(true);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          log.error('Search failed', { error: String(err) });
          setResults([]);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }, 300);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
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

  const handleCreatePatient = useCallback(async () => {
    if (!newPatient.nombre || !newPatient.apellido) {
      alert('Nombre y apellido son requeridos');
      return;
    }

    setCreating(true);
    try {
      // Backend expects full ISO 8601 datetime
      const today = new Date().toISOString();
      
      const created = await createPatient({
        nombre: newPatient.nombre,
        apellido: newPatient.apellido,
        fecha_nacimiento: today,
      });

      onPatientSelect(created.id, created.name);
      setSearch(created.name);
      setShowCreateForm(false);
      setShowDropdown(false);
      setNewPatient({ nombre: '', apellido: '', email: '', phone: '' });
    } catch (err) {
      log.error('Create patient failed', { error: String(err) });
      const errorMessage = err instanceof Error ? err.message : 'Error al crear paciente';
      alert(errorMessage);
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
    setNewPatient({ nombre: '', apellido: '', email: '', phone: '' });
  }, []);

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

  const handleNewPatientChange = useCallback((form: NewPatientForm) => {
    setNewPatient(form);
  }, []);

  // Field validation
  const [touchedFields, setTouchedFields] = useState<Set<string>>(new Set());

  const handleFieldBlur = useCallback((fieldName: string) => {
    setTouchedFields(prev => new Set(prev).add(fieldName));
  }, []);

  const getFieldError = useCallback((fieldName: string): string | undefined => {
    if (!touchedFields.has(fieldName)) return undefined;

    if (fieldName === 'nombre' && !newPatient.nombre) {
      return 'Nombre es requerido';
    }
    if (fieldName === 'apellido' && !newPatient.apellido) {
      return 'Apellido es requerido';
    }
    return undefined;
  }, [touchedFields, newPatient]);

  return {
    dropdownRef,
    search,
    setSearch,
    results,
    showDropdown,
    loading,
    showCreateForm,
    newPatient,
    setNewPatient,
    handleNewPatientChange,
    creating,
    handleSelectPatient,
    handleCreatePatient,
    openCreateForm,
    closeCreateForm,
    clearSearch,
    handleFocus,
    handleFieldBlur,
    getFieldError,
  };
}
