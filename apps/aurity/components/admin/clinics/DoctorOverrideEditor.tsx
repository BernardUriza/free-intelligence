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
    <div className="p-4 bg-yellow-900/20 border border-yellow-700/30 rounded-lg">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <Shield className="w-4 h-4 text-yellow-400" />
        <span className="text-sm font-medium text-yellow-300">
          Override de Límite (Superadmin)
        </span>
      </div>

      {/* Info */}
      <p className="text-xs text-yellow-400/70 mb-3">
        El límite del plan ({limits.plan_display_name}) es{' '}
        {limits.max_allowed === null ? 'ilimitado' : `${limits.max_allowed} doctores`}.
        {limits.has_override && ' Actualmente hay un override activo.'}
      </p>

      {/* Error */}
      {error && (
        <div className="p-2 bg-red-500/20 border border-red-500/30 rounded mb-3">
          <p className="text-xs text-red-300">{error}</p>
        </div>
      )}

      {/* Editor */}
      {isEditing ? (
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-yellow-400/70 mb-1">
              Nuevo límite de doctores
            </label>
            <input
              type="number"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="Dejar vacío para usar límite del plan"
              min={1}
              max={1000}
              className="w-full px-3 py-2 bg-slate-900 border border-yellow-700/50 rounded-lg text-white text-sm focus:border-yellow-500 focus:ring-1 focus:ring-yellow-500 outline-none"
            />
            <p className="text-xs text-slate-500 mt-1">
              Dejar vacío para usar el límite del plan
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-3 py-1.5 bg-yellow-600 hover:bg-yellow-500 disabled:bg-slate-700 text-white text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5"
            >
              {saving ? (
                <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <Save className="w-3 h-3" />
              )}
              Guardar
            </button>
            <button
              onClick={handleCancel}
              disabled={saving}
              className="px-3 py-1.5 text-slate-400 hover:text-white text-xs transition-colors flex items-center gap-1.5"
            >
              <X className="w-3 h-3" />
              Cancelar
            </button>
            {limits.has_override && (
              <button
                onClick={handleRemoveOverride}
                disabled={saving}
                className="ml-auto px-3 py-1.5 text-red-400 hover:text-red-300 text-xs transition-colors flex items-center gap-1.5"
              >
                <AlertTriangle className="w-3 h-3" />
                Eliminar override
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-between">
          <div>
            <span className="text-sm text-slate-300">
              {limits.has_override ? (
                <>
                  Override activo:{' '}
                  <span className="text-yellow-300 font-medium">
                    {limits.max_allowed} doctores
                  </span>
                </>
              ) : (
                <span className="text-slate-500">Sin override configurado</span>
              )}
            </span>
          </div>
          <button
            onClick={() => setIsEditing(true)}
            className="px-3 py-1.5 bg-yellow-600/20 hover:bg-yellow-600/30 text-yellow-300 text-xs font-medium rounded-lg transition-colors"
          >
            {limits.has_override ? 'Editar' : 'Configurar override'}
          </button>
        </div>
      )}
    </div>
  );
}
