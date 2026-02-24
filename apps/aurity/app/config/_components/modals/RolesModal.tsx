/**
 * RolesModal
 *
 * Displays RBAC role definitions, assignment flow, and JWT claim info.
 */

import { Button } from '@/components/ui/button';
import { getRoleName, getRoleBadgeColor, ROLES } from '@aurity-standalone/hooks/useRBAC';
import type { ModalProps } from '../types';

export function RolesModal({ onClose }: ModalProps) {
  return (
    <div className="fi-modal-backdrop" onClick={onClose}>
      <div className="cfg-modal-lg" onClick={(e) => e.stopPropagation()}>
        <div className="cfg-modal-header">
          <h2 className="fi-title-xl">Configurar Roles & Permisos</h2>
          <p className="cfg-subtitle-gap">Configuración RBAC del sistema</p>
        </div>

        <div className="cfg-section-body">
          <RoleManagementGuide />
          <RolesList />
          <PermissionsNote />
        </div>

        <div className="cfg-modal-footer">
          <Button onClick={onClose} variant="secondary" size="sm">
            Cerrar
          </Button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Co-located sub-components
// ---------------------------------------------------------------------------

function RoleManagementGuide() {
  return (
    <div className="cfg-info-card-purple">
      <h3 className="cfg-info-title-purple">Gestión de Roles</h3>
      <ol className="cfg-list-ordered">
        <li>
          <strong className="cfg-strong-white">Roles disponibles</strong>
          <div className="cfg-code-mini">FI-superadmin, FI-clinician</div>
        </li>
        <li>
          <strong className="cfg-strong-white">Asignación de roles</strong>
          <p className="cfg-indent-text">
            Los roles se asignan al registrar usuarios o via el panel de administración de
            usuarios.
          </p>
        </li>
        <li>
          <strong className="cfg-strong-white">JWT Claims</strong>
          <p className="cfg-indent-text">
            Los roles se incluyen automáticamente en el JWT token bajo el claim
            &quot;roles&quot;.
          </p>
        </li>
      </ol>
    </div>
  );
}

function RolesList() {
  return (
    <div className="cfg-section-inner">
      <h3 className="cfg-title-gap">Roles Definidos en AURITY</h3>
      <div className="cfg-roles-list">
        {Object.entries(ROLES).map(([, role]) => (
          <div key={role} className="cfg-role-row-modal">
            <div className="fi-flex-gap">
              <span className={`admin-role-badge-md ${getRoleBadgeColor(role)}`}>
                {getRoleName(role)}
              </span>
              <code className="cfg-role-code-modal">{role}</code>
            </div>
            <span className="cfg-role-muted">
              {role === ROLES.SUPERADMIN && 'Full access'}
              {role === ROLES.CLINICIAN && 'Clinical operations'}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function PermissionsNote() {
  return (
    <div className="cfg-info-card-blue">
      <h3 className="cfg-info-title-blue">Permisos por Rol</h3>
      <p className="cfg-info-text-blue-body">
        Cada rol tiene permisos predefinidos que se verifican automáticamente en cada endpoint
        del backend. El primer usuario registrado recibe el rol FI-superadmin automáticamente.
      </p>
    </div>
  );
}
