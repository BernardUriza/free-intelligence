'use client';

/**
 * Settings section with password change action.
 */

import { Button } from '@/components/ui/button';

interface SettingsSectionProps {
  onChangePassword: () => void;
}

export function SettingsSection({ onChangePassword }: SettingsSectionProps) {
  return (
    <div className="prof-section">
      <h3 className="fi-title prof-section-title">Configuración</h3>
      <p className="prof-section-desc">
        Para cambiar tu información de perfil, contacta al administrador.
      </p>
      <div className="prof-button-row">
        <Button variant="secondary" size="sm" onClick={onChangePassword}>
          Cambiar contraseña
        </Button>
      </div>
    </div>
  );
}
