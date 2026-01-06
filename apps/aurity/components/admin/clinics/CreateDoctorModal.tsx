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

const ROLES: { value: ClinicRole; label: string }[] = [
  { value: 'DOCTOR', label: 'Doctor' },
  { value: 'ADMIN', label: 'Administrador' },
  { value: 'STAFF', label: 'Staff' },
  { value: 'OWNER', label: 'Propietario' },
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
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 rounded-xl max-w-lg w-full shadow-2xl border border-slate-700">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/20 rounded-lg">
              <UserPlus className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">
                Agregar Doctor
              </h2>
              <p className="text-xs text-slate-400">{clinicName}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {/* Limit Error */}
          {limitError && (
            <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-red-300 font-medium">
                  Límite de doctores alcanzado
                </p>
                <p className="text-xs text-red-400 mt-1">
                  Esta clínica tiene {limitError.current}/{limitError.max}{' '}
                  doctores ({limitError.plan}). Contacta al administrador para
                  aumentar el límite.
                </p>
              </div>
            </div>
          )}

          {/* General Error */}
          {error && (
            <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg">
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}

          {/* Name Row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Nombre *
              </label>
              <input
                type="text"
                name="nombre"
                value={formData.nombre}
                onChange={handleChange}
                placeholder="Juan"
                required
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Apellido *
              </label>
              <input
                type="text"
                name="apellido"
                value={formData.apellido}
                onChange={handleChange}
                placeholder="Pérez"
                required
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
              />
            </div>
          </div>

          {/* Specialty */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">
              Especialidad
            </label>
            <select
              name="especialidad"
              value={formData.especialidad}
              onChange={handleChange}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
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
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Email</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="doctor@clinica.com"
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Cédula Profesional
              </label>
              <input
                type="text"
                name="cedula_profesional"
                value={formData.cedula_profesional}
                onChange={handleChange}
                placeholder="12345678"
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
              />
            </div>
          </div>

          {/* Consultation Duration */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">
              Duración de consulta (minutos)
            </label>
            <input
              type="number"
              name="avg_consultation_minutes"
              value={formData.avg_consultation_minutes}
              onChange={handleChange}
              min={5}
              max={180}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
            />
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t border-slate-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-300 hover:text-white transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving || !isValid}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
            >
              {saving ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Guardando...
                </>
              ) : (
                <>
                  <UserPlus className="w-4 h-4" />
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
