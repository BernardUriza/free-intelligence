'use client';

/**
 * Patient Info Modal - Pre-Consultation Form
 *
 * Captures required patient information before starting a medical recording.
 * Data is saved to HDF5 session metadata.
 *
 * Created: 2025-11-17
 */

import React, { useState } from 'react';
import { X, User, Calendar, FileText, AlertCircle, Lightbulb } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface PatientInfoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (patientInfo: PatientInfo) => void;
}

export interface PatientInfo {
  patient_name: string;
  patient_age?: string;
  patient_id?: string;
  chief_complaint?: string;
}

export function PatientInfoModal({ isOpen, onClose, onSubmit }: PatientInfoModalProps) {
  const [patientName, setPatientName] = useState('');
  const [patientAge, setPatientAge] = useState('');
  const [patientId, setPatientId] = useState('');
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validate required field
    if (!patientName.trim()) {
      setError('El nombre del paciente es obligatorio');
      return;
    }

    // Submit patient info
    onSubmit({
      patient_name: patientName.trim(),
      patient_age: patientAge.trim() || undefined,
      patient_id: patientId.trim() || undefined,
      chief_complaint: chiefComplaint.trim() || undefined,
    });

    // Reset form
    setPatientName('');
    setPatientAge('');
    setPatientId('');
    setChiefComplaint('');
    setError('');
  };

  const handleCancel = () => {
    setError('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fi-modal-backdrop bg-black/80">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl max-w-md w-full">
        {/* Header */}
        <div className="flex items-center justify-between p-6 fi-border-bottom">
          <div className="fi-flex-gap-md">
            <div className="w-10 h-10 bg-cyan-500/20 rounded-xl flex items-center justify-center">
              <User className="h-5 w-5 fi-text-info" />
            </div>
            <div>
              <h2 className="fi-title">Información del Paciente</h2>
              <p className="fi-subtitle">Requerido antes de iniciar la consulta</p>
            </div>
          </div>
          <Button
            onClick={handleCancel}
            variant="ghost"
            size="sm"
            icon={X}
            aria-label="Cerrar"
          />
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Error Alert */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 flex items-start gap-2">
              <AlertCircle className="h-5 w-5 fi-text-error flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}

          {/* Patient Name (Required) */}
          <div>
            <label htmlFor="patient-name" className="fi-label">
              Nombre del Paciente <span className="fi-text-error">*</span>
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                id="patient-name"
                type="text"
                value={patientName}
                onChange={(e) => {
                  setPatientName(e.target.value);
                  setError('');
                }}
                placeholder="Ej: María González López"
                className="fi-input-cyan fi-input-with-icon-left"
                autoFocus
                required
              />
            </div>
          </div>

          {/* Patient Age (Optional) */}
          <div>
            <label htmlFor="patient-age" className="fi-label">
              Edad <span className="text-slate-500 text-xs">(opcional)</span>
            </label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                id="patient-age"
                type="text"
                value={patientAge}
                onChange={(e) => setPatientAge(e.target.value)}
                placeholder="Ej: 42 años"
                className="fi-input-cyan fi-input-with-icon-left"
              />
            </div>
          </div>

          {/* Patient ID / Expediente (Optional) */}
          <div>
            <label htmlFor="patient-id" className="fi-label">
              No. Expediente <span className="text-slate-500 text-xs">(opcional)</span>
            </label>
            <div className="relative">
              <FileText className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                id="patient-id"
                type="text"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                placeholder="Ej: EXP-2024-001234"
                className="fi-input-cyan fi-input-with-icon-left"
              />
            </div>
          </div>

          {/* Chief Complaint (Optional) */}
          <div>
            <label htmlFor="chief-complaint" className="fi-label">
              Motivo de Consulta <span className="text-slate-500 text-xs">(opcional)</span>
            </label>
            <textarea
              id="chief-complaint"
              value={chiefComplaint}
              onChange={(e) => setChiefComplaint(e.target.value)}
              placeholder="Ej: Dolor de cabeza intenso desde hace 3 días"
              rows={3}
              className="fi-input-cyan resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <Button
              type="button"
              onClick={handleCancel}
              variant="secondary"
              className="flex-1"
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              variant="cyan"
              className="flex-1"
            >
              Iniciar Consulta
            </Button>
          </div>
        </form>

        {/* Footer Note */}
        <div className="px-6 pb-6">
          <div className="fi-note">
            <p className="fi-text-xs flex items-start gap-2">
              <Lightbulb className="w-4 h-4 flex-shrink-0 mt-0.5 text-yellow-400" strokeWidth={1.5} aria-hidden="true" />
              <span>Esta información se guarda de forma segura en el expediente electrónico y
              facilita la identificación de la consulta.</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
