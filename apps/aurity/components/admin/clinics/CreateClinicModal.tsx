/**
 * CreateClinicModal Component
 *
 * Modal form for creating a new clinic.
 * Single Responsibility: Clinic creation form.
 *
 * Card: FI-CHECKIN-002
 */

import { useState } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import type { ClinicCreate } from '@/lib/api/clinics';

interface CreateClinicModalProps {
  onClose: () => void;
  onCreate: (data: ClinicCreate) => Promise<void>;
}

export function CreateClinicModal({ onClose, onCreate }: CreateClinicModalProps) {
  const [formData, setFormData] = useState<ClinicCreate>({
    name: '',
    specialty: 'general',
    welcome_message: '',
    payments_enabled: false,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError('El nombre es requerido');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onCreate(formData);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear la clínica');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="clinic-modal-overlay">
      <div className="clinic-modal">
        <div className="clinic-modal-header">
          <h2 className="fi-title-xl">Nueva Clínica</h2>
          <button onClick={onClose} className="fi-btn-close">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="clinic-modal-form">
          <div>
            <label className="block fi-subtitle mb-1">Nombre *</label>
            <Input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Nombre de la clínica"
            />
          </div>

          <div>
            <label className="block fi-subtitle mb-1">Especialidad</label>
            <Select value={formData.specialty} onValueChange={(val) => setFormData({ ...formData, specialty: val })}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Seleccionar especialidad" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="general">General</SelectItem>
                <SelectItem value="pediatria">Pediatría</SelectItem>
                <SelectItem value="cardiologia">Cardiología</SelectItem>
                <SelectItem value="dermatologia">Dermatología</SelectItem>
                <SelectItem value="ginecologia">Ginecología</SelectItem>
                <SelectItem value="oftalmologia">Oftalmología</SelectItem>
                <SelectItem value="traumatologia">Traumatología</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="block fi-subtitle mb-1">Mensaje de bienvenida</label>
            <textarea
              value={formData.welcome_message}
              onChange={(e) => setFormData({ ...formData, welcome_message: e.target.value })}
              className="clinic-modal-textarea"
              rows={2}
              placeholder="¡Bienvenido a nuestra clínica!"
            />
          </div>

          <div className="clinic-modal-checkbox-group">
            <input
              type="checkbox"
              id="payments"
              checked={formData.payments_enabled}
              onChange={(e) => setFormData({ ...formData, payments_enabled: e.target.checked })}
              className="clinic-modal-checkbox"
            />
            <label htmlFor="payments" className="fi-subtitle">
              Habilitar pagos (Stripe)
            </label>
          </div>

          {error && (
            <div className="clinic-modal-error">{error}</div>
          )}

          <div className="clinic-modal-actions">
            <Button
              type="button"
              onClick={onClose}
              variant="secondary"
              fullWidth
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={saving}
              variant="indigo"
              fullWidth
              loading={saving}
            >
              Crear Clínica
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
