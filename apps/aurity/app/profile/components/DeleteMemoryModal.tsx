'use client';

/**
 * Confirmation modal for deleting longitudinal memory.
 */

import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface DeleteMemoryModalProps {
  isDeleting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function DeleteMemoryModal({ isDeleting, onConfirm, onCancel }: DeleteMemoryModalProps) {
  return (
    <div className="prof-modal-overlay">
      <div className="prof-modal-content">
        <h3 className="prof-modal-title fi-text-error">
          <AlertTriangle className="prof-icon-md" strokeWidth={1.5} aria-hidden="true" />
          Confirmar eliminación
        </h3>
        <p className="fi-text prof-modal-body">
          Estás a punto de eliminar <strong>TODA la memoria longitudinal</strong>:
        </p>
        <ul className="prof-modal-list">
          <li>Todos los archivos HDF5 de sesiones</li>
          <li>Todos los mensajes de chat</li>
          <li>Historial de conversaciones</li>
        </ul>
        <p className="prof-modal-warning">
          <CheckCircle2 className="prof-modal-warning-icon" strokeWidth={1.5} aria-hidden="true" />
          Se mantendrán: configuraciones de personalidades y registros de pacientes
        </p>
        <p className="fi-text-error prof-modal-irreversible">
          Esta acción NO se puede deshacer.
        </p>
        <div className="prof-modal-actions">
          <Button
            variant="secondary"
            onClick={onCancel}
            disabled={isDeleting}
            className="prof-modal-btn"
          >
            Cancelar
          </Button>
          <Button
            variant="danger"
            onClick={onConfirm}
            disabled={isDeleting}
            className="prof-modal-btn"
          >
            {isDeleting ? 'Eliminando...' : 'Sí, eliminar todo'}
          </Button>
        </div>
      </div>
    </div>
  );
}
