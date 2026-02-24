/**
 * RolesManagementSection
 *
 * Current user info, available roles, permission matrix,
 * and superadmin/auth configuration details.
 */

import { Star } from 'lucide-react';
import { getRoleName, getRoleBadgeColor, ROLES, type Role } from '@aurity-standalone/hooks/useRBAC';
import { PERMISSION_MATRIX } from '../constants';
import type { RolesManagementSectionProps } from '../types';

export function RolesManagementSection({
  email,
  userId,
  isSuperAdmin,
  roles,
}: RolesManagementSectionProps) {
  return (
    <div className="cfg-section-card">
      <div className="cfg-section-header">
        <h2 className="fi-title">Gestión de Usuarios & Roles</h2>
        <p className="fi-subtitle">Administración centralizada de permisos RBAC</p>
      </div>
      <div className="cfg-section-body-lg">
        <CurrentUserCard
          email={email}
          userId={userId}
          isSuperAdmin={isSuperAdmin}
          roles={roles}
        />
        <AvailableRoles />
        <PermissionMatrix />
        <SuperadminConfig />
        <AuthIntegrationNote />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Co-located sub-components
// ---------------------------------------------------------------------------

function CurrentUserCard({
  email,
  userId,
  isSuperAdmin,
  roles,
}: RolesManagementSectionProps) {
  return (
    <div className="cfg-user-card">
      <div className="cfg-header-gap">
        <h3 className="fi-title-sm">Usuario Actual</h3>
        {isSuperAdmin && <span className="cfg-superadmin-tag">SUPERADMIN</span>}
      </div>
      <div className="fi-stack-sm">
        <div className="fi-flex-between cfg-user-info-row">
          <span className="cfg-user-label">Email:</span>
          <span className="cfg-user-email">{email}</span>
        </div>
        <div className="fi-flex-between cfg-user-info-row">
          <span className="cfg-user-label">User ID:</span>
          <span className="cfg-user-id">{userId}</span>
        </div>
        <div className="cfg-user-roles-row">
          <span className="cfg-user-label">Roles:</span>
          <div className="cfg-user-roles-wrap">
            {roles.length > 0 ? (
              roles.map((role) => (
                <span
                  key={role}
                  className={`admin-role-badge-md ${getRoleBadgeColor(role as Role)}`}
                >
                  {getRoleName(role as Role)}
                </span>
              ))
            ) : (
              <span className="cfg-user-no-roles">Sin roles asignados</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function AvailableRoles() {
  return (
    <div>
      <h3 className="cfg-title-gap">Roles Disponibles</h3>
      <div className="cfg-roles-list">
        {Object.entries(ROLES).map(([, role]) => (
          <div key={role} className="fi-list-item">
            <div className="fi-flex-gap-md">
              <span className={`admin-role-badge-lg ${getRoleBadgeColor(role)}`}>
                {getRoleName(role)}
              </span>
              <span className="cfg-role-code">{role}</span>
            </div>
            <div className="fi-text-xs-muted">
              {role === ROLES.SUPERADMIN && 'Acceso completo al sistema'}
              {role === ROLES.CLINICIAN && 'Operaciones clínicas'}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PermissionMatrix() {
  return (
    <div>
      <h3 className="cfg-title-gap">Permisos por Rol</h3>
      <div className="cfg-perm-table-wrap">
        <table className="cfg-perm-table">
          <thead>
            <tr className="fi-border-bottom">
              <th className="cfg-perm-th-left">Permiso</th>
              <th className="cfg-perm-th-purple">SUPERADMIN</th>
              <th className="cfg-perm-th-green">CLINICIAN</th>
            </tr>
          </thead>
          <tbody>
            {PERMISSION_MATRIX.map((row) => (
              <tr key={row.label} className="cfg-perm-row">
                <td className="cfg-perm-td">{row.label}</td>
                <PermissionCell allowed={row.superadmin} />
                <PermissionCell allowed={row.clinician} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PermissionCell({ allowed }: { allowed: boolean }) {
  return allowed ? (
    <td className="cfg-perm-center">Si</td>
  ) : (
    <td className="cfg-perm-na">--</td>
  );
}

function SuperadminConfig() {
  return (
    <div className="cfg-info-card-purple">
      <h3 className="cfg-info-title-purple-flex">
        <Star className="cfg-star-sm" />
        Configuración Superadmin
      </h3>
      <p className="cfg-info-text-purple">
        Lista de emails con acceso completo al sistema (configurado via{' '}
        <code className="cfg-code-inline-purple">NEXT_PUBLIC_SUPERADMIN_EMAILS</code>)
      </p>
      <div className="cfg-code-block-purple">
        <code className="cfg-code-text-purple">
          NEXT_PUBLIC_SUPERADMIN_EMAILS=bernarduriza@gmail.com,admin@aurity.app
        </code>
      </div>
      <p className="cfg-note-gap">
        Nota: Cambios requieren rebuild del frontend (pnpm build)
      </p>
    </div>
  );
}

function AuthIntegrationNote() {
  return (
    <div className="cfg-info-card-blue">
      <h3 className="cfg-info-title-blue">Autenticación JWT</h3>
      <p className="cfg-info-text-blue">
        Los roles se asignan al registrar usuarios y se incluyen en el JWT token bajo el claim:
      </p>
      <code className="cfg-code-block-blue">
        roles: [&quot;FI-clinician&quot;, &quot;FI-superadmin&quot;]
      </code>
    </div>
  );
}
