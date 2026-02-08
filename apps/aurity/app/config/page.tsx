'use client';

/**
 * System Configuration Page
 * SUPERADMIN ONLY - Uses RBAC hook for access control
 *
 * Global system settings, user management, and role administration
 */

import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Star } from 'lucide-react';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { configHeader } from '@/config/page-headers';
import { useRBAC, getRoleName, getRoleBadgeColor, ROLES } from '@aurity-standalone/hooks/useRBAC';
import { UserManagement } from '@/components/admin/user-management';
import { confirmDanger, showSuccess, showError } from '@/lib/swal';

export default function ConfigPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const { isSuperAdmin, isLoading: rbacLoading, roles } = useRBAC();
  const router = useRouter();
  const [resettingOnboarding, setResettingOnboarding] = useState(false);
  const [showUserManagement, setShowUserManagement] = useState(false);
  const [showRolesModal, setShowRolesModal] = useState(false);
  const [showAuditModal, setShowAuditModal] = useState(false);

  const isLoading = authLoading || rbacLoading;

  // Check superadmin access
  useEffect(() => {
    if (!isLoading && isAuthenticated && !isSuperAdmin) {
      console.warn('[ConfigPage] Access denied - not superadmin');
      router.push('/unauthorized');
    }
  }, [isLoading, isAuthenticated, isSuperAdmin, router]);

  // Handle onboarding reset
  const handleResetOnboarding = async () => {
    const confirmed = await confirmDanger({
      title: '¿Reiniciar onboarding?',
      text: 'Esto eliminará todo el progreso guardado.',
      confirmText: 'Reiniciar',
    });
    if (!confirmed) return;

    setResettingOnboarding(true);

    try {
      // Clear onboarding localStorage
      localStorage.removeItem('fi_onboarding_progress');
      localStorage.removeItem('fi_onboarding_conversation');
      localStorage.removeItem('aurity_onboarding_completed');
      localStorage.removeItem('fi_onboarding_survey');

      console.log('[OK] Onboarding reset successfully');

      await showSuccess('Onboarding reiniciado', 'Redirigiendo...');
      setResettingOnboarding(false);
      router.push('/onboarding');
    } catch (error) {
      console.error('Failed to reset onboarding:', error);
      await showError('Error', 'No se pudo reiniciar el onboarding');
      setResettingOnboarding(false);
    }
  };

  if (isLoading) {
    return (
      <div className="layout-loading-screen">
        <div className="cfg-loading-spinner"></div>
      </div>
    );
  }

  if (!isAuthenticated || !isSuperAdmin) {
    return null; // Will redirect via useEffect
  }

  // Generate header config
  const headerConfig = configHeader();

  return (
    <AppTemplate headerConfig={headerConfig} maxWidth="full" padding="0" showWatermark={true} showGeometricBg={true}>
      <div className="cfg-page-container">
        {/* Superadmin Badge */}
        <div className="cfg-superadmin-banner">
          <div className="fi-flex-gap">
<Star className="cfg-superadmin-star" />
            <span className="cfg-superadmin-label">SUPERADMIN Access</span>
            <span className="cfg-superadmin-dot">·</span>
            <span className="cfg-superadmin-email">{user?.email}</span>
          </div>
        </div>

        {/* Configuration Sections */}
        <div className="cfg-sections">
          {/* System Settings */}
          <div className="cfg-section-card">
            <div className="cfg-section-header">
              <h2 className="fi-title">Sistema</h2>
              <p className="fi-subtitle">Configuración global del sistema</p>
            </div>
            <div className="cfg-section-body">
              <div className="fi-settings-row-bordered">
                <div>
                  <p className="cfg-setting-label">Modo de Mantenimiento</p>
                  <p className="fi-subtitle">Bloquear acceso para usuarios no-admin</p>
                </div>
                <Button variant="secondary" size="sm">
                  Desactivado
                </Button>
              </div>

              <div className="fi-settings-row-bordered">
                <div>
                  <p className="cfg-setting-label">Logs del Sistema</p>
                  <p className="fi-subtitle">Ver logs de errores y auditoría</p>
                </div>
                <Button variant="primary" size="sm">
                  Ver Logs
                </Button>
              </div>

              <div className="fi-settings-row-bordered">
                <div>
                  <p className="cfg-setting-label">Base de Datos</p>
                  <p className="fi-subtitle">Estado de HDF5 corpus</p>
                </div>
                <Button variant="secondary" size="sm">
                  Inspeccionar
                </Button>
              </div>

              <div className="fi-settings-row">
                <div>
                  <p className="cfg-setting-label">Reiniciar Onboarding</p>
                  <p className="fi-subtitle">Resetear estado de onboarding para testing</p>
                </div>
                <Button
                  onClick={handleResetOnboarding}
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

          {/* Feature Flags */}
          <div className="cfg-section-card">
            <div className="cfg-section-header">
              <h2 className="fi-title">Feature Flags</h2>
              <p className="fi-subtitle">Activar/desactivar características experimentales</p>
            </div>
            <div className="cfg-section-body">
              <div className="fi-settings-row-bordered">
                <div>
                  <p className="cfg-setting-label">Demo Mode</p>
                  <p className="fi-subtitle">Modo demo con TTS simulado</p>
                </div>
                <div className="fi-flex-gap">
                  <span className="cfg-toggle-label-active">Activo</span>
                  <div className="cfg-toggle-on">
                    <div className="cfg-toggle-knob-right"></div>
                  </div>
                </div>
              </div>

              <div className="fi-settings-row-bordered">
                <div>
                  <p className="cfg-setting-label">Timeline View</p>
                  <p className="fi-subtitle">Vista cronológica de eventos</p>
                </div>
                <div className="fi-flex-gap">
                  <span className="cfg-toggle-label-active">Activo</span>
                  <div className="cfg-toggle-on">
                    <div className="cfg-toggle-knob-right"></div>
                  </div>
                </div>
              </div>

              <div className="fi-settings-row">
                <div>
                  <p className="cfg-setting-label">Advanced Diarization</p>
                  <p className="fi-subtitle">Separación de voces mejorada</p>
                </div>
                <div className="fi-flex-gap">
                  <span className="cfg-toggle-label-inactive">Inactivo</span>
                  <div className="cfg-toggle-off">
                    <div className="cfg-toggle-knob-left"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Security & Access */}
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
                <Button
                  onClick={() => setShowUserManagement(true)}
                  variant="primary"
                  size="sm"
                >
                  Gestionar Usuarios
                </Button>
              </div>

              <div className="fi-settings-row-bordered">
                <div>
                  <p className="cfg-setting-label">Roles & Permisos</p>
                  <p className="fi-subtitle">Configurar RBAC</p>
                </div>
                <Button
                  onClick={() => setShowRolesModal(true)}
                  variant="secondary"
                  size="sm"
                >
                  Configurar
                </Button>
              </div>

              <div className="fi-settings-row">
                <div>
                  <p className="cfg-setting-label">Audit Trail</p>
                  <p className="fi-subtitle">Registro completo de cambios</p>
                </div>
                <Button
                  onClick={() => setShowAuditModal(true)}
                  variant="primary"
                  size="sm"
                >
                  Ver Auditoría
                </Button>
              </div>
            </div>
          </div>

          {/* User & Role Management */}
          <div className="cfg-section-card">
            <div className="cfg-section-header">
              <h2 className="fi-title">Gestión de Usuarios & Roles</h2>
              <p className="fi-subtitle">Administración centralizada de permisos RBAC</p>
            </div>
            <div className="cfg-section-body-lg">
              {/* Current User Info */}
              <div className="cfg-user-card">
                <div className="cfg-header-gap">
                  <h3 className="fi-title-sm">Usuario Actual</h3>
                  {isSuperAdmin && (
                    <span className="cfg-superadmin-tag">
                      SUPERADMIN
                    </span>
                  )}
                </div>
                <div className="fi-stack-sm">
                  <div className="fi-flex-between cfg-user-info-row">
                    <span className="cfg-user-label">Email:</span>
                    <span className="cfg-user-email">{user?.email}</span>
                  </div>
                  <div className="fi-flex-between cfg-user-info-row">
                    <span className="cfg-user-label">User ID:</span>
                    <span className="cfg-user-id">
                      {user?.sub}
                    </span>
                  </div>
                  <div className="cfg-user-roles-row">
                    <span className="cfg-user-label">Roles:</span>
                    <div className="cfg-user-roles-wrap">
                      {roles.length > 0 ? (
                        roles.map(role => (
                          <span
                            key={role}
                            className={`admin-role-badge-md ${getRoleBadgeColor(role)}`}
                          >
                            {getRoleName(role)}
                          </span>
                        ))
                      ) : (
                        <span className="cfg-user-no-roles">Sin roles asignados</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Roles Definition */}
              <div>
                <h3 className="cfg-title-gap">Roles Disponibles</h3>
                <div className="cfg-roles-list">
                  {Object.entries(ROLES).map(([_key, role]) => (
                    <div
                      key={role}
                      className="fi-list-item"
                    >
                      <div className="fi-flex-gap-md">
                        <span className={`admin-role-badge-lg ${getRoleBadgeColor(role)}`}>
                          {getRoleName(role)}
                        </span>
                        <span className="cfg-role-code">{role}</span>
                      </div>
                      <div className="fi-text-xs-muted">
                        {role === ROLES.SUPERADMIN && 'Acceso completo al sistema'}
                        {role === ROLES.CLINICIAN && 'Operaciones clinicas'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Permission Matrix */}
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
                      <tr className="cfg-perm-row">
                        <td className="cfg-perm-td">Gestionar Sistema</td>
                        <td className="cfg-perm-center">Si</td>
                        <td className="cfg-perm-na">--</td>
                      </tr>
                      <tr className="cfg-perm-row">
                        <td className="cfg-perm-td">Ver Logs</td>
                        <td className="cfg-perm-center">Si</td>
                        <td className="cfg-perm-na">--</td>
                      </tr>
                      <tr className="cfg-perm-row">
                        <td className="cfg-perm-td">Gestionar Usuarios</td>
                        <td className="cfg-perm-center">Si</td>
                        <td className="cfg-perm-na">--</td>
                      </tr>
                      <tr className="cfg-perm-row">
                        <td className="cfg-perm-td">Crear Sesion</td>
                        <td className="cfg-perm-center">Si</td>
                        <td className="cfg-perm-center">Si</td>
                      </tr>
                      <tr className="cfg-perm-row">
                        <td className="cfg-perm-td">Ver Sesion</td>
                        <td className="cfg-perm-center">Si</td>
                        <td className="cfg-perm-center">Si</td>
                      </tr>
                      <tr className="cfg-perm-row">
                        <td className="cfg-perm-td">Exportar Datos</td>
                        <td className="cfg-perm-center">Si</td>
                        <td className="cfg-perm-center">Si</td>
                      </tr>
                      <tr>
                        <td className="cfg-perm-td">Eliminar Sesion</td>
                        <td className="cfg-perm-center">Si</td>
                        <td className="cfg-perm-na">--</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Superadmin Configuration */}
              <div className="cfg-info-card-purple">
                <h3 className="cfg-info-title-purple-flex">
                  <Star className="cfg-star-sm" />
                  Configuración Superadmin
                </h3>
                <p className="cfg-info-text-purple">
                  Lista de emails con acceso completo al sistema (configurado via <code className="cfg-code-inline-purple">NEXT_PUBLIC_SUPERADMIN_EMAILS</code>)
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

              {/* Auth Integration Note */}
              <div className="cfg-info-card-blue">
                <h3 className="cfg-info-title-blue">
                   Autenticación JWT
                </h3>
                <p className="cfg-info-text-blue">
                  Los roles se asignan al registrar usuarios y se incluyen en el JWT token bajo el claim:
                </p>
                <code className="cfg-code-block-blue">
                  roles: [&quot;FI-clinician&quot;, &quot;FI-superadmin&quot;]
                </code>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Modals */}
      {/* User Management - Full Featured */}
      {showUserManagement && (
        <UserManagement onClose={() => setShowUserManagement(false)} />
      )}

      {/* Roles Configuration Modal */}
      {showRolesModal && (
        <div className="fi-modal-backdrop" onClick={() => setShowRolesModal(false)}>
          <div className="cfg-modal-lg" onClick={(e) => e.stopPropagation()}>
            <div className="cfg-modal-header">
              <h2 className="fi-title-xl">Configurar Roles & Permisos</h2>
              <p className="cfg-subtitle-gap">Configuración RBAC del sistema</p>
            </div>
            <div className="cfg-section-body">
              <div className="cfg-info-card-purple">
                <h3 className="cfg-info-title-purple"> Gestión de Roles</h3>
                <ol className="cfg-list-ordered">
                  <li>
                    <strong className="cfg-strong-white">Roles disponibles</strong>
                    <div className="cfg-code-mini">
                      FI-superadmin, FI-clinician
                    </div>
                  </li>
                  <li>
                    <strong className="cfg-strong-white">Asignación de roles</strong>
                    <p className="cfg-indent-text">Los roles se asignan al registrar usuarios o via el panel de administración de usuarios.</p>
                  </li>
                  <li>
                    <strong className="cfg-strong-white">JWT Claims</strong>
                    <p className="cfg-indent-text">Los roles se incluyen automáticamente en el JWT token bajo el claim &quot;roles&quot;.</p>
                  </li>
                </ol>
              </div>

              <div className="cfg-section-inner">
                <h3 className="cfg-title-gap">Roles Definidos en AURITY</h3>
                <div className="cfg-roles-list">
                  {Object.entries(ROLES).map(([_key, role]) => (
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

              <div className="cfg-info-card-blue">
                <h3 className="cfg-info-title-blue"> Permisos por Rol</h3>
                <p className="cfg-info-text-blue-body">
                  Cada rol tiene permisos predefinidos que se verifican automáticamente en cada endpoint del backend.
                  El primer usuario registrado recibe el rol FI-superadmin automáticamente.
                </p>
              </div>
            </div>
            <div className="cfg-modal-footer">
              <Button
                onClick={() => setShowRolesModal(false)}
                variant="secondary"
                size="sm"
              >
                Cerrar
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Audit Trail Modal */}
      {showAuditModal && (
        <div className="fi-modal-backdrop" onClick={() => setShowAuditModal(false)}>
          <div className="cfg-modal-md" onClick={(e) => e.stopPropagation()}>
            <div className="cfg-modal-header">
              <h2 className="fi-title-xl">Audit Trail</h2>
              <p className="cfg-subtitle-gap">Registro de auditoría del sistema</p>
            </div>
            <div className="cfg-section-body">
              <div className="cfg-info-card-emerald">
                <h3 className="cfg-info-title-emerald">Si Backend Audit Trail Activo</h3>
                <p className="cfg-info-text-body">
                  El backend ya registra todas las operaciones en HDF5:
                </p>
                <ul className="cfg-list-bullets">
                  <li>Operaciones LLM (generate, embed)</li>
                  <li>Exportaciones de datos</li>
                  <li>Búsquedas en corpus</li>
                  <li>Operaciones críticas (delete)</li>
                </ul>
                <div className="cfg-code-wrap">
                  <code className="cfg-code-text-success">
                    Location: /storage/corpus.h5:/audit_logs
                  </code>
                </div>
              </div>

              <div className="cfg-section-inner">
                <h3 className="cfg-title-gap">Estructura de Logs</h3>
                <div className="cfg-pre-wrap">
                  <pre className="cfg-pre-text">
{`{
  "timestamp": "2025-11-20T02:45:12Z",
  "operation": "llm_generate",
  "user_id": "user-123...",
  "user_email": "doctor@hospital.com",
  "payload_hash": "sha256:abc...",
  "result_hash": "sha256:def...",
  "cost_usd": 0.0042,
  "level": "info"
}`}
                  </pre>
                </div>
              </div>

              <div className="cfg-info-card-yellow">
                <h3 className="cfg-info-title-yellow"> UI de Auditoría - En Desarrollo</h3>
                <p className="cfg-info-text-yellow">
                  Próximamente: Interfaz para visualizar y filtrar logs de auditoría
                </p>
                <ul className="cfg-list-bullets-tight">
                  <li>Timeline de eventos con filtros</li>
                  <li>Búsqueda por usuario, operación, fecha</li>
                  <li>Export de logs (CSV, JSON)</li>
                  <li>Alertas en tiempo real</li>
                  <li>Estadísticas de uso por usuario</li>
                </ul>
              </div>

              <div className="cfg-info-card-blue">
                <h3 className="cfg-info-title-blue"> Inspección Manual</h3>
                <p className="cfg-info-text-body-sm">
                  Puedes inspeccionar los logs manualmente usando:
                </p>
                <div className="cfg-code-wrap-plain">
                  <code className="cfg-code-text-primary">
                    python backend/tools/inspect_corpus.py --audit-logs
                  </code>
                </div>
              </div>
            </div>
            <div className="cfg-modal-footer-single">
              <Button
                onClick={() => setShowAuditModal(false)}
                variant="secondary"
                size="sm"
              >
                Cerrar
              </Button>
            </div>
          </div>
        </div>
      )}
    </AppTemplate>
  );
}
