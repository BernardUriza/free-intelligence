'use client';

/**
 * Danger zone section with memory deletion trigger.
 */

import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface DangerZoneProps {
  onDeleteClick: () => void;
}

export function DangerZone({ onDeleteClick }: DangerZoneProps) {
  return (
    <div className="prof-danger-zone">
      <h3 className="prof-danger-title fi-text-error">Zona Peligrosa</h3>
      <p className="prof-danger-desc">
        Estas acciones son irreversibles. Los datos eliminados no se pueden recuperar.
      </p>
      <Button variant="danger" size="sm" onClick={onDeleteClick}>
        <Trash2 className="prof-icon-sm" strokeWidth={1.5} aria-hidden="true" />
        Borrar toda la memoria longitudinal
      </Button>
      <p className="prof-danger-footnote">
        Elimina todas las sesiones HDF5 y mensajes de chat. Configuraciones de personalidades y pacientes se mantienen.
      </p>
    </div>
  );
}
