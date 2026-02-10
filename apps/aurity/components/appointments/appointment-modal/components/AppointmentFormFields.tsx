'use client';

/**
 * AppointmentFormFields Component
 *
 * Form fields for doctor, date/time, type, duration, reason, notes.
 */

import { Calendar, Clock, Stethoscope, FileText } from 'lucide-react';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import type { AppointmentDraft, Doctor } from '../types';

interface AppointmentFormFieldsProps {
  form: AppointmentDraft;
  doctors: Doctor[];
  onFieldChange: <K extends keyof AppointmentDraft>(field: K, value: AppointmentDraft[K]) => void;
  hideDoctorField?: boolean;
}

export function AppointmentFormFields({ form, doctors, onFieldChange, hideDoctorField = false }: AppointmentFormFieldsProps) {
  return (
    <>
      {/* Doctor Selection - hidden when doctor is implicit (e.g., MedicalAI) */}
      {!hideDoctorField && (
        <div>
          <label className="apt-field-label">
            <Stethoscope className="fi-icon-sm" />
            Doctor
          </label>
          <Select value={form.doctor_id} onValueChange={(val) => onFieldChange('doctor_id', val)}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Seleccionar doctor" />
            </SelectTrigger>
            <SelectContent>
              {doctors.map((doctor) => (
                <SelectItem key={doctor.doctor_id} value={doctor.doctor_id}>
                  {doctor.display_name} - {doctor.especialidad}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Date and Time */}
      <div className="fi-grid-2">
        <div>
          <label className="apt-field-label">
            <Calendar className="fi-icon-sm" />
            Fecha
          </label>
          <input
            type="date"
            required
            value={form.scheduled_date}
            onChange={(e) => onFieldChange('scheduled_date', e.target.value)}
            className="fi-input-cyan"
          />
        </div>
        <div>
          <label className="apt-field-label">
            <Clock className="fi-icon-sm" />
            Hora
          </label>
          <input
            type="time"
            required
            value={form.scheduled_time}
            onChange={(e) => onFieldChange('scheduled_time', e.target.value)}
            className="fi-input-cyan"
          />
        </div>
      </div>

      {/* Appointment Type and Duration */}
      <div className="fi-grid-2">
        <div>
          <label className="fi-label block">Tipo de Cita</label>
          <Select
            value={form.appointment_type}
            onValueChange={(val) => onFieldChange('appointment_type', val as AppointmentDraft['appointment_type'])}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Seleccionar tipo" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="FIRST_TIME">Primera Vez</SelectItem>
              <SelectItem value="FOLLOW_UP">Seguimiento</SelectItem>
              <SelectItem value="PROCEDURE">Procedimiento</SelectItem>
              <SelectItem value="EMERGENCY">Emergencia</SelectItem>
              <SelectItem value="TELEMEDICINE">Telemedicina</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="fi-label block">Duración (minutos)</label>
          <input
            type="number"
            required
            min={5}
            max={180}
            step={5}
            value={Number.isFinite(form.estimated_duration) ? form.estimated_duration : ('' as any)}
            onChange={(e) => {
              const v = e.target.value;
              const n = parseInt(v, 10);
              onFieldChange(
                'estimated_duration',
                Number.isFinite(n) ? n : v === '' ? 0 : form.estimated_duration
              );
            }}
            className="fi-input-cyan"
          />
        </div>
      </div>

      {/* Reason */}
      <div>
        <label className="apt-field-label">
          <FileText className="fi-icon-sm" />
          Motivo de Consulta
        </label>
        <textarea
          required
          value={form.reason}
          onChange={(e) => onFieldChange('reason', e.target.value)}
          placeholder="ej: Dolor de cabeza persistente"
          rows={2}
          className="fi-input-cyan resize-none"
        />
      </div>

      {/* Notes (Optional) */}
      <div>
        <label className="fi-label block">Notas Adicionales (Opcional)</label>
        <textarea
          value={form.notes}
          onChange={(e) => onFieldChange('notes', e.target.value)}
          placeholder="Información adicional relevante..."
          rows={3}
          className="fi-input-cyan resize-none"
        />
      </div>
    </>
  );
}
