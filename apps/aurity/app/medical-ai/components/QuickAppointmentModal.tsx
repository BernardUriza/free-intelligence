/**
 * QuickAppointmentModal
 *
 * Simplified modal for creating appointments directly from medical-ai.
 * Pre-populates time from calendar slot click.
 */

'use client';

import { useState, useEffect, useMemo } from 'react';
import { X, Search, User, Clock, Calendar, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { Patient } from '@aurity-standalone/types/patient';

// ============================================================================
// Types
// ============================================================================

interface QuickAppointmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: QuickAppointmentData) => Promise<void>;
  patients: Patient[];
  initialDate?: Date;
  loading?: boolean;
}

export interface QuickAppointmentData {
  patient_id: string;
  patient: Patient;
  scheduled_at: Date;
  estimated_duration: number;
  reason: string;
  appointment_type: string;
}

// ============================================================================
// Component
// ============================================================================

export function QuickAppointmentModal({
  isOpen,
  onClose,
  onSubmit,
  patients,
  initialDate,
  loading = false,
}: QuickAppointmentModalProps) {
  // Form state
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [scheduledDate, setScheduledDate] = useState('');
  const [scheduledTime, setScheduledTime] = useState('');
  const [duration, setDuration] = useState(30);
  const [reason, setReason] = useState('');
  const [appointmentType, setAppointmentType] = useState('follow_up');
  const [submitting, setSubmitting] = useState(false);

  // Filter patients by search
  const filteredPatients = useMemo(() => {
    if (!searchQuery.trim()) return patients.slice(0, 10); // Show first 10
    return patients.filter((p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [patients, searchQuery]);

  // Initialize date from prop
  useEffect(() => {
    if (initialDate) {
      const date = new Date(initialDate);
      setScheduledDate(date.toISOString().split('T')[0]);
      setScheduledTime(
        `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
      );
    } else {
      const now = new Date();
      setScheduledDate(now.toISOString().split('T')[0]);
      setScheduledTime('09:00');
    }
  }, [initialDate, isOpen]);

  // Reset form when modal closes
  useEffect(() => {
    if (!isOpen) {
      setSelectedPatient(null);
      setSearchQuery('');
      setReason('');
      setDuration(30);
      setAppointmentType('follow_up');
    }
  }, [isOpen]);

  // Handle submit
  const handleSubmit = async () => {
    if (!selectedPatient || !scheduledDate || !scheduledTime) return;

    setSubmitting(true);
    try {
      const scheduled_at = new Date(`${scheduledDate}T${scheduledTime}`);

      await onSubmit({
        patient_id: selectedPatient.patient_id,
        patient: selectedPatient,
        scheduled_at,
        estimated_duration: duration,
        reason,
        appointment_type: appointmentType,
      });

      onClose();
    } catch (error) {
      console.error('[QuickAppointmentModal] Submit error:', error);
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-indigo-400" />
            <h2 className="text-lg font-semibold text-white">Nueva Cita</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4 overflow-y-auto max-h-[calc(90vh-140px)]">
          {/* Patient Selection */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              <User className="w-4 h-4 inline mr-1" />
              Paciente
            </label>

            {selectedPatient ? (
              <div className="flex items-center justify-between bg-slate-800 p-3 rounded-lg">
                <div>
                  <p className="text-white font-medium">{selectedPatient.name}</p>
                  <p className="text-sm text-slate-400">
                    {selectedPatient.date_of_birth}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedPatient(null)}
                >
                  Cambiar
                </Button>
              </div>
            ) : (
              <>
                {/* Search */}
                <div className="relative mb-2">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Buscar paciente..."
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                {/* Patient list */}
                <div className="max-h-40 overflow-y-auto space-y-1 bg-slate-800/50 rounded-lg p-2">
                  {filteredPatients.length === 0 ? (
                    <p className="text-center text-slate-500 py-4 text-sm">
                      No se encontraron pacientes
                    </p>
                  ) : (
                    filteredPatients.map((patient) => (
                      <button
                        key={patient.patient_id}
                        onClick={() => setSelectedPatient(patient)}
                        className="w-full flex items-center gap-3 p-2 hover:bg-slate-700 rounded-lg text-left transition-colors"
                      >
                        <div className="w-8 h-8 bg-indigo-500/20 rounded-full flex items-center justify-center">
                          <User className="w-4 h-4 text-indigo-400" />
                        </div>
                        <div>
                          <p className="text-white text-sm">{patient.name}</p>
                          <p className="text-xs text-slate-400">
                            {patient.date_of_birth}
                          </p>
                        </div>
                      </button>
                    ))
                  )}
                </div>
              </>
            )}
          </div>

          {/* Date & Time */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                <Calendar className="w-4 h-4 inline mr-1" />
                Fecha
              </label>
              <input
                type="date"
                value={scheduledDate}
                onChange={(e) => setScheduledDate(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                <Clock className="w-4 h-4 inline mr-1" />
                Hora
              </label>
              <input
                type="time"
                value={scheduledTime}
                onChange={(e) => setScheduledTime(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          {/* Duration */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Duración
            </label>
            <div className="flex gap-2">
              {[15, 30, 45, 60].map((mins) => (
                <button
                  key={mins}
                  onClick={() => setDuration(mins)}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                    duration === mins
                      ? 'bg-indigo-500 text-white'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {mins} min
                </button>
              ))}
            </div>
          </div>

          {/* Appointment Type */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Tipo
            </label>
            <select
              value={appointmentType}
              onChange={(e) => setAppointmentType(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="follow_up">Seguimiento</option>
              <option value="first_visit">Primera consulta</option>
              <option value="procedure">Procedimiento</option>
              <option value="emergency">Urgencia</option>
              <option value="telemedicine">Telemedicina</option>
            </select>
          </div>

          {/* Reason */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              <FileText className="w-4 h-4 inline mr-1" />
              Motivo (opcional)
            </label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Ej: Control de presión arterial"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-slate-700">
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={!selectedPatient || submitting || loading}
            loading={submitting}
          >
            Crear y Atender
          </Button>
        </div>
      </div>
    </div>
  );
}
