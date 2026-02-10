/**
 * ClinicInfoGrid Component
 *
 * Displays clinic metadata: timezone, primary color, welcome message.
 * Single Responsibility: Clinic info display.
 *
 * Card: FI-CHECKIN-002
 */

import type { Clinic } from '@/lib/api/clinics';

interface ClinicInfoGridProps {
  clinic: Clinic;
}

export function ClinicInfoGrid({ clinic }: ClinicInfoGridProps) {
  return (
    <div className="clinic-info-grid">
      <div>
        <span className="clinic-info-label">Zona horaria</span>
        <p className="clinic-info-value">{clinic.timezone}</p>
      </div>
      <div>
        <span className="clinic-info-label">Color primario</span>
        <div className="fi-flex-gap">
          <div
            className="clinic-color-swatch"
            style={{ backgroundColor: clinic.primary_color || '#6366f1' }}
          />
          <span className="clinic-info-value">{clinic.primary_color}</span>
        </div>
      </div>
      <div className="clinic-info-full">
        <span className="clinic-info-label">Mensaje de bienvenida</span>
        <p className="clinic-info-value">{clinic.welcome_message || '-'}</p>
      </div>
    </div>
  );
}
