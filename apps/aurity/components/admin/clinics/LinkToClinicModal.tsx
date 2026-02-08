/**
 * LinkToClinicModal Component
 *
 * Modal for non-superadmin users to link themselves to a clinic.
 * Single Responsibility: User-clinic membership creation.
 *
 * Card: FI-CHECKIN-002
 */

import { useState } from 'react';
import { Loader2, X, UserPlus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import type { ClinicRole } from '@/lib/api/clinics';

interface LinkForm {
  nombre: string;
  apellido: string;
  especialidad: string;
  role: ClinicRole;
}

interface LinkToClinicModalProps {
  clinicName: string;
  linking: boolean;
  onSubmit: (form: LinkForm) => Promise<boolean | undefined>;
  onClose: () => void;
}

export function LinkToClinicModal({
  clinicName,
  linking,
  onSubmit,
  onClose,
}: LinkToClinicModalProps) {
  const [form, setForm] = useState<LinkForm>({
    nombre: '',
    apellido: '',
    especialidad: '',
    role: 'OWNER',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = await onSubmit(form);
    if (success) {
      onClose();
    }
  };

  return (
    <div className="clinic-modal-overlay">
      <div className="clinic-modal">
        <div className="clinic-modal-header">
          <h2 className="fi-title-xl">Vincularme a {clinicName}</h2>
          <button onClick={onClose} className="fi-btn-close">
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="clinic-modal-hint">
          Al vincularte a esta clínica, aparecerás como miembro del equipo y podrás gestionar citas y pacientes.
        </p>

        <form onSubmit={handleSubmit} className="clinic-modal-form">
          <div className="clinic-modal-row">
            <div>
              <label className="block fi-subtitle mb-1">Nombre *</label>
              <Input
                value={form.nombre}
                onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                placeholder="Tu nombre"
                required
                className="clinic-input-dark"
              />
            </div>
            <div>
              <label className="block fi-subtitle mb-1">Apellido *</label>
              <Input
                value={form.apellido}
                onChange={(e) => setForm({ ...form, apellido: e.target.value })}
                placeholder="Tu apellido"
                required
                className="clinic-input-dark"
              />
            </div>
          </div>

          <div>
            <label className="block fi-subtitle mb-1">Especialidad</label>
            <Input
              value={form.especialidad}
              onChange={(e) => setForm({ ...form, especialidad: e.target.value })}
              placeholder="Ej: Medicina General, Cardiología"
              className="clinic-input-dark"
            />
          </div>

          <div>
            <label className="block fi-subtitle mb-1">Rol en la clínica</label>
            <Select value={form.role} onValueChange={(val) => setForm({ ...form, role: val as ClinicRole })}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Seleccionar rol" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="OWNER">Propietario (Owner)</SelectItem>
                <SelectItem value="ADMIN">Administrador</SelectItem>
                <SelectItem value="DOCTOR">Doctor</SelectItem>
                <SelectItem value="STAFF">Staff</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="clinic-modal-actions">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="flex-1"
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={linking || !form.nombre || !form.apellido}
              className="clinic-modal-submit-btn"
            >
              {linking ? (
                <Loader2 className="clinic-modal-submit-icon animate-spin" />
              ) : (
                <UserPlus className="clinic-modal-submit-icon" />
              )}
              Vincularme
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
