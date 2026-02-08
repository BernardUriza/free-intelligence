'use client';

/**
 * CreateDoctorModal
 *
 * Modal for creating a new doctor in a clinic.
 * Handles doctor limit validation (403 error).
 *
 * File: apps/aurity/components/admin/clinics/CreateDoctorModal.tsx
 * Created: 2025-12-31
 */

import { useState } from 'react';
import { X, UserPlus, AlertCircle } from 'lucide-react';
import type { Doctor, DoctorCreate, ClinicRole } from '@/lib/api/clinics';
import { createDoctorWithLimitCheck } from '@/lib/api/clinics';

interface CreateDoctorModalProps {
  clinicId: string;
  clinicName: string;
  onClose: () => void;
  onCreate: (doctor: Doctor) => void;
}

const SPECIALTIES = [
  'General',
  'Pediatría',
  'Cardiología',
  'Dermatología',
  'Ginecología',
  'Oftalmología',
  'Traumatología',
  'Neurología',
  'Psiquiatría',
  'Otorrinolaringología',
];

export function CreateDoctorModal({
  clinicId,
  clinicName,
  onClose,
  onCreate,
}: CreateDoctorModalProps) {
  const [formData, setFormData] = useState<DoctorCreate>({
    nombre: '',
    apellido: '',
    especialidad: '',
    cedula_profesional: '',
    email: '',
    avg_consultation_minutes: 30,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [limitError, setLimitError] = useState<{
    current: number;
    max: number;
    plan: string;
  } | null>(null);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'avg_consultation_minutes' ? parseInt(value, 10) : value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setLimitError(null);

    try {
      const result = await createDoctorWithLimitCheck(clinicId, formData);

      if (result.success) {
        onCreate(result.doctor);
        onClose();
      } else {
        // Doctor limit exceeded
        setLimitError({
          current: result.error.current_count,
          max: result.error.max_allowed,
          plan: result.error.plan_name,
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear doctor');
    } finally {
      setSaving(false);
    }
  };

  const isValid = formData.nombre.trim() && formData.apellido.trim();

  return (
    <div className="cdoc-overlay">
      <div className="cdoc-container">
        {/* Header */}
        <div className="cdoc-header">
          <div className="cdoc-header-info">
            <div className="cdoc-header-icon-wrap">
              <UserPlus className="cdoc-header-icon" />
            </div>
            <div>
              <h2 className="cdoc-title">
                Agregar Doctor
              </h2>
              <p className="cdoc-subtitle">{clinicName}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="cdoc-close-btn"
          >
            <X className="cdoc-close-icon" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="cdoc-form">
          {/* Limit Error */}
          {limitError && (
            <div className="cdoc-limit-error">
              <AlertCircle className="cdoc-limit-error-icon" />
              <div>
                <p className="cdoc-limit-error-title">
                  Límite de doctores alcanzado
                </p>
                <p className="cdoc-limit-error-detail">
                  Esta clínica tiene {limitError.current}/{limitError.max}{' '}
                  doctores ({limitError.plan}). Contacta al administrador para
                  aumentar el límite.
                </p>
              </div>
            </div>
          )}

          {/* General Error */}
          {error && (
            <div className="cdoc-error">
              <p className="cdoc-error-text">{error}</p>
            </div>
          )}

          {/* Name Row */}
          <div className="cdoc-row">
            <div>
              <label className="cdoc-label">
                Nombre *
              </label>
              <input
                type="text"
                name="nombre"
                value={formData.nombre}
                onChange={handleChange}
                placeholder="Juan"
                required
                className="cdoc-input"
              />
            </div>
            <div>
              <label className="cdoc-label">
                Apellido *
              </label>
              <input
                type="text"
                name="apellido"
                value={formData.apellido}
                onChange={handleChange}
                placeholder="Pérez"
                required
                className="cdoc-input"
              />
            </div>
          </div>

          {/* Specialty */}
          <div>
            <label className="cdoc-label">
              Especialidad
            </label>
            <select
              name="especialidad"
              value={formData.especialidad}
              onChange={handleChange}
              className="cdoc-input"
            >
              <option value="">Seleccionar...</option>
              {SPECIALTIES.map((spec) => (
                <option key={spec} value={spec.toLowerCase()}>
                  {spec}
                </option>
              ))}
            </select>
          </div>

          {/* Email and Cedula Row */}
          <div className="cdoc-row">
            <div>
              <label className="cdoc-label">Email</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="doctor@clinica.com"
                className="cdoc-input"
              />
            </div>
            <div>
              <label className="cdoc-label">
                Cédula Profesional
              </label>
              <input
                type="text"
                name="cedula_profesional"
                value={formData.cedula_profesional}
                onChange={handleChange}
                placeholder="12345678"
                className="cdoc-input"
              />
            </div>
          </div>

          {/* Consultation Duration */}
          <div>
            <label className="cdoc-label">
              Duración de consulta (minutos)
            </label>
            <input
              type="number"
              name="avg_consultation_minutes"
              value={formData.avg_consultation_minutes}
              onChange={handleChange}
              min={5}
              max={180}
              className="cdoc-input"
            />
          </div>

          {/* Actions */}
          <div className="cdoc-actions">
            <button
              type="button"
              onClick={onClose}
              className="cdoc-cancel-btn"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving || !isValid}
              className="cdoc-submit-btn"
            >
              {saving ? (
                <>
                  <div className="cdoc-spinner" />
                  Guardando...
                </>
              ) : (
                <>
                  <UserPlus className="cdoc-btn-icon" />
                  Crear Doctor
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
