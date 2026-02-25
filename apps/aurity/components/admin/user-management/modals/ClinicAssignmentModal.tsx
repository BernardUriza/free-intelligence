'use client';

import { useState } from 'react';
import { X, Building2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { toastError, toastSuccess } from '@/lib/swal';
import { adminAssignUserToClinic, type Clinic, type ClinicRole, type AdminUserClinicInfo } from '@/lib/api/clinics';
import { createLogger } from '@/lib/internal/logger';
import type { User } from '../types';
import { CLINIC_ROLES } from '../types';

const log = createLogger('ClinicAssignment');

interface ClinicAssignmentModalProps {
  user: User;
  clinics: Clinic[];
  currentClinicInfo?: AdminUserClinicInfo;
  onClose: () => void;
  onAssigned: (clinicInfo: AdminUserClinicInfo) => void;
}

export function ClinicAssignmentModal({
  user,
  clinics,
  currentClinicInfo,
  onClose,
  onAssigned,
}: ClinicAssignmentModalProps) {
  const [selectedClinicId, setSelectedClinicId] = useState(currentClinicInfo?.clinic_id || '');
  const [selectedRole, setSelectedRole] = useState<ClinicRole>(
    (currentClinicInfo?.clinic_role as ClinicRole) || 'STAFF'
  );
  const [nombre, setNombre] = useState(currentClinicInfo?.nombre || user.name?.split(' ')[0] || '');
  const [apellido, setApellido] = useState(
    currentClinicInfo?.apellido || user.name?.split(' ').slice(1).join(' ') || ''
  );
  const [especialidad, setEspecialidad] = useState(currentClinicInfo?.apellido || '');
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedClinicId || !nombre.trim() || !apellido.trim()) {
      toastError('Complete todos los campos requeridos');
      return;
    }

    setSaving(true);
    try {
      const result = await adminAssignUserToClinic({
        user_id: user.user_id,
        email: user.email,
        clinic_id: selectedClinicId,
        role: selectedRole,
        nombre: nombre.trim(),
        apellido: apellido.trim(),
        especialidad: especialidad.trim() || undefined,
      });

      if (result.success && result.membership) {
        toastSuccess('Usuario asignado a clínica');
        onAssigned({
          user_id: user.user_id,
          email: user.email,
          doctor_id: result.membership.doctor_id,
          clinic_id: result.membership.clinic_id,
          clinic_name: result.membership.clinic_name,
          clinic_role: result.membership.clinic_role as ClinicRole,
          nombre: result.membership.nombre,
          apellido: result.membership.apellido,
          is_linked: true,
        });
      }
    } catch (error) {
      log.error('Failed to assign user to clinic', { error: String(error) });
      toastError('Error al asignar usuario a clínica');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fi-modal-backdrop z-[60]" onClick={onClose}>
      <div className="fi-modal-sm p-6" onClick={(e) => e.stopPropagation()}>
        <div className="fi-flex-between mb-4">
          <h3 className="fi-title fi-flex-gap">
            <Building2 className="w-5 h-5 fi-text-primary" />
            Asignar a Clínica
          </h3>
          <button onClick={onClose} className="fi-btn-icon-sm">
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="fi-subtitle mb-4">
          Asignando a: <span className="text-white font-mono">{user.email}</span>
        </p>

        {currentClinicInfo?.is_linked && (
          <div className="mb-4 p-3 bg-blue-900/20 border border-blue-700/30 rounded-lg">
            <p className="text-xs text-blue-300">
              Actualmente vinculado a: <strong>{currentClinicInfo.clinic_name}</strong> como{' '}
              <strong>{currentClinicInfo.clinic_role}</strong>
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="fi-stack-lg">
          <div>
            <label className="fi-label">Clínica *</label>
            <Select value={selectedClinicId} onValueChange={setSelectedClinicId}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Seleccionar clínica..." />
              </SelectTrigger>
              <SelectContent>
                {clinics.map((clinic) => (
                  <SelectItem key={clinic.clinic_id} value={clinic.clinic_id}>
                    {clinic.name} ({clinic.specialty})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="fi-label">Rol en Clínica *</label>
            <Select value={selectedRole} onValueChange={(val) => setSelectedRole(val as ClinicRole)}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Seleccionar rol" />
              </SelectTrigger>
              <SelectContent>
                {CLINIC_ROLES.map((role) => (
                  <SelectItem key={role.value} value={role.value}>
                    {role.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="fi-label">Nombre *</label>
              <input
                type="text"
                required
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder="Juan"
                className="fi-input-blue"
              />
            </div>
            <div>
              <label className="fi-label">Apellido *</label>
              <input
                type="text"
                required
                value={apellido}
                onChange={(e) => setApellido(e.target.value)}
                placeholder="Pérez"
                className="fi-input-blue"
              />
            </div>
          </div>

          <div>
            <label className="fi-label">Especialidad</label>
            <input
              type="text"
              value={especialidad}
              onChange={(e) => setEspecialidad(e.target.value)}
              placeholder="Medicina General (opcional)"
              className="fi-input-blue"
            />
          </div>

          <div className="flex gap-2 pt-4">
            <Button type="button" onClick={onClose} variant="secondary" fullWidth>
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={saving || !selectedClinicId || !nombre.trim() || !apellido.trim()}
              variant="primary"
              fullWidth
              loading={saving}
            >
              Asignar
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
