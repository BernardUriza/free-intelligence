'use client';

/**
 * DoctorOverrideEditor
 *
 * Allows superadmin to set a custom doctor limit override for a clinic.
 * Only visible to users with FI-superadmin role.
 *
 * File: apps/aurity/components/admin/clinics/DoctorOverrideEditor.tsx
 * Created: 2025-12-31
 */

import { useState } from 'react';
import { Shield, Save, X, AlertTriangle } from 'lucide-react';
import type { DoctorLimitInfo } from '@/lib/api/clinics';
import { updateDoctorOverride } from '@/lib/api/clinics';

interface DoctorOverrideEditorProps {
  clinicId: string;
  clinicName: string;
  limits: DoctorLimitInfo;
  isSuperAdmin: boolean;
  onUpdate: () => void;
}

export function DoctorOverrideEditor({
  clinicId,
  clinicName,
  limits,
  isSuperAdmin,
  onUpdate,
}: DoctorOverrideEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [value, setValue] = useState<string>(
    limits.has_override && limits.max_allowed !== null
      ? limits.max_allowed.toString()
      : ''
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Only show for superadmin
  if (!isSuperAdmin) {
    return null;
  }

  const handleSave = async () => {
    setSaving(true);
    setError(null);

    try {
      const override = value.trim() ? parseInt(value, 10) : null;

      // Validate
      if (override !== null && (override < 1 || override > 1000)) {
        setError('El límite debe estar entre 1 y 1000');
        setSaving(false);
        return;
      }

      await updateDoctorOverride(clinicId, override);
      setIsEditing(false);
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setValue(
      limits.has_override && limits.max_allowed !== null
        ? limits.max_allowed.toString()
        : ''
    );
    setIsEditing(false);
    setError(null);
  };

  const handleRemoveOverride = async () => {
    setSaving(true);
    setError(null);

    try {
      await updateDoctorOverride(clinicId, null);
      setValue('');
      setIsEditing(false);
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al eliminar override');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="dov-container">
      {/* Header */}
      <div className="dov-header">
        <Shield className="dov-header-icon" />
        <span className="dov-header-title">
          Override de Límite (Superadmin)
        </span>
      </div>

      {/* Info */}
      <p className="dov-info">
        El límite del plan ({limits.plan_display_name}) es{' '}
        {limits.max_allowed === null ? 'ilimitado' : `${limits.max_allowed} doctores`}.
        {limits.has_override && ' Actualmente hay un override activo.'}
      </p>

      {/* Error */}
      {error && (
        <div className="dov-error">
          <p className="dov-error-text">{error}</p>
        </div>
      )}

      {/* Editor */}
      {isEditing ? (
        <div className="dov-editor">
          <div>
            <label className="dov-label">
              Nuevo límite de doctores
            </label>
            <input
              type="number"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="Dejar vacío para usar límite del plan"
              min={1}
              max={1000}
              className="dov-input"
            />
            <p className="dov-hint">
              Dejar vacío para usar el límite del plan
            </p>
          </div>

          <div className="dov-btn-row">
            <button
              onClick={handleSave}
              disabled={saving}
              className="dov-save-btn"
            >
              {saving ? (
                <div className="dov-spinner" />
              ) : (
                <Save className="dov-btn-icon" />
              )}
              Guardar
            </button>
            <button
              onClick={handleCancel}
              disabled={saving}
              className="dov-cancel-btn"
            >
              <X className="dov-btn-icon" />
              Cancelar
            </button>
            {limits.has_override && (
              <button
                onClick={handleRemoveOverride}
                disabled={saving}
                className="dov-remove-btn"
              >
                <AlertTriangle className="dov-btn-icon" />
                Eliminar override
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="dov-display">
          <div>
            <span className="dov-status-text">
              {limits.has_override ? (
                <>
                  Override activo:{' '}
                  <span className="dov-status-value">
                    {limits.max_allowed} doctores
                  </span>
                </>
              ) : (
                <span className="dov-status-empty">Sin override configurado</span>
              )}
            </span>
          </div>
          <button
            onClick={() => setIsEditing(true)}
            className="dov-edit-btn"
          >
            {limits.has_override ? 'Editar' : 'Configurar override'}
          </button>
        </div>
      )}
    </div>
  );
}
