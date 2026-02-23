/**
 * SystemSettingsSection
 *
 * Global system configuration: maintenance mode, logs,
 * database inspection, and onboarding reset.
 */

import { Button } from '@/components/ui/button';
import type { SystemSettingsSectionProps } from '../types';

export function SystemSettingsSection({
  resettingOnboarding,
  onResetOnboarding,
}: SystemSettingsSectionProps) {
  return (
    <div className="cfg-section-card">
      <div className="cfg-section-header">
        <h2 className="fi-title">Sistema</h2>
        <p className="fi-subtitle">Configuración global del sistema</p>
      </div>
      <div className="cfg-section-body">
        <SettingRow
          label="Modo de Mantenimiento"
          description="Bloquear acceso para usuarios no-admin"
          buttonLabel="Desactivado"
          buttonVariant="secondary"
        />

        <SettingRow
          label="Logs del Sistema"
          description="Ver logs de errores y auditoría"
          buttonLabel="Ver Logs"
          buttonVariant="primary"
        />

        <SettingRow
          label="Base de Datos"
          description="Estado de HDF5 corpus"
          buttonLabel="Inspeccionar"
          buttonVariant="secondary"
        />

        <div className="fi-settings-row">
          <div>
            <p className="cfg-setting-label">Reiniciar Onboarding</p>
            <p className="fi-subtitle">Resetear estado de onboarding para testing</p>
          </div>
          <Button
            onClick={onResetOnboarding}
            disabled={resettingOnboarding}
            variant="danger"
            size="sm"
            loading={resettingOnboarding}
            className="cfg-reset-btn-override"
          >
            {resettingOnboarding ? 'Reseteando...' : 'Resetear'}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Co-located helper — static setting row with no interactive handler
// ---------------------------------------------------------------------------

function SettingRow({
  label,
  description,
  buttonLabel,
  buttonVariant,
}: {
  label: string;
  description: string;
  buttonLabel: string;
  buttonVariant: 'primary' | 'secondary';
}) {
  return (
    <div className="fi-settings-row-bordered">
      <div>
        <p className="cfg-setting-label">{label}</p>
        <p className="fi-subtitle">{description}</p>
      </div>
      <Button variant={buttonVariant} size="sm">
        {buttonLabel}
      </Button>
    </div>
  );
}
