/**
 * SecuritySection
 *
 * Links to user management, roles configuration, and audit trail.
 * Each "Gestionar" button opens its respective modal via callbacks.
 */

import { Button } from '@/components/ui/button';
import type { SecuritySectionProps } from '../types';

export function SecuritySection({
  onOpenUserManagement,
  onOpenRolesModal,
  onOpenAuditModal,
}: SecuritySectionProps) {
  return (
    <div className="cfg-section-card">
      <div className="cfg-section-header">
        <h2 className="fi-title">Seguridad & Acceso</h2>
        <p className="fi-subtitle">Gestión de roles y permisos</p>
      </div>
      <div className="cfg-section-body">
        <div className="fi-settings-row-bordered">
          <div>
            <p className="cfg-setting-label">Usuarios Activos</p>
            <p className="fi-subtitle">Gestionar usuarios del sistema</p>
          </div>
          <Button onClick={onOpenUserManagement} variant="primary" size="sm">
            Gestionar Usuarios
          </Button>
        </div>

        <div className="fi-settings-row-bordered">
          <div>
            <p className="cfg-setting-label">Roles & Permisos</p>
            <p className="fi-subtitle">Configurar RBAC</p>
          </div>
          <Button onClick={onOpenRolesModal} variant="secondary" size="sm">
            Configurar
          </Button>
        </div>

        <div className="fi-settings-row">
          <div>
            <p className="cfg-setting-label">Audit Trail</p>
            <p className="fi-subtitle">Registro completo de cambios</p>
          </div>
          <Button onClick={onOpenAuditModal} variant="primary" size="sm">
            Ver Auditoría
          </Button>
        </div>
      </div>
    </div>
  );
}
