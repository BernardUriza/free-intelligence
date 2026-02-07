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
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="animate-spin h-12 w-12 border-4 border-purple-400 border-t-transparent rounded-full"></div>
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
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Superadmin Badge */}
        <div className="mb-6 bg-purple-900/20 border border-purple-500/30 rounded-lg p-4">
          <div className="fi-flex-gap">
<Star className="w-5 h-5 fi-text-purple fill-purple-400" />
            <span className="text-purple-300 font-medium">SUPERADMIN Access</span>
            <span className="fi-text-purple/60 text-sm">·</span>
            <span className="fi-text-purple/80 text-sm">{user?.email}</span>
          </div>
        </div>

        {/* Configuration Sections */}
        <div className="space-y-6">
          {/* System Settings */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-lg overflow-hidden">
            <div className="px-6 py-4 bg-slate-900/50 fi-border-bottom">
              <h2 className="fi-title">Sistema</h2>
              <p className="fi-subtitle">Configuración global del sistema</p>
            </div>
            <div className="p-6 space-y-4">
              <div className="fi-settings-row-bordered">
                <div>
                  <p className="text-white font-medium">Modo de Mantenimiento</p>
                  <p className="fi-subtitle">Bloquear acceso para usuarios no-admin</p>
                </div>
                <Button variant="secondary" size="sm">
                  Desactivado
                </Button>
              </div>

              <div className="fi-settings-row-bordered">
                <div>
                  <p className="text-white font-medium">Logs del Sistema</p>
                  <p className="fi-subtitle">Ver logs de errores y auditoría</p>
                </div>
                <Button variant="primary" size="sm">
                  Ver Logs
                </Button>
              </div>

              <div className="fi-settings-row-bordered">
                <div>
                  <p className="text-white font-medium">Base de Datos</p>
                  <p className="fi-subtitle">Estado de HDF5 corpus</p>
                </div>
                <Button variant="secondary" size="sm">
                  Inspeccionar
                </Button>
              </div>

              <div className="fi-settings-row">
                <div>
                  <p className="text-white font-medium">Reiniciar Onboarding</p>
                  <p className="fi-subtitle">Resetear estado de onboarding para testing</p>
                </div>
                <Button
                  onClick={handleResetOnboarding}
                  disabled={resettingOnboarding}
                  variant="danger"
                  size="sm"
                  loading={resettingOnboarding}
                  className="bg-orange-600 hover:bg-orange-700"
                >
                  {resettingOnboarding ? 'Reseteando...' : 'Resetear'}
                </Button>
              </div>
            </div>
          </div>

          {/* Feature Flags */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-lg overflow-hidden">
            <div className="px-6 py-4 bg-slate-900/50 fi-border-bottom">
              <h2 className="fi-title">Feature Flags</h2>
              <p className="fi-subtitle">Activar/desactivar características experimentales</p>
            </div>
            <div className="p-6 space-y-4">
              <div className="fi-settings-row-bordered">
                <div>
                  <p className="text-white font-medium">Demo Mode</p>
                  <p className="fi-subtitle">Modo demo con TTS simulado</p>
                </div>
                <div className="fi-flex-gap">
                  <span className="fi-text-green text-sm font-medium">Activo</span>
                  <div className="w-12 h-6 bg-green-600 rounded-full relative cursor-pointer">
                    <div className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full"></div>
                  </div>
                </div>
              </div>

              <div className="fi-settings-row-bordered">
                <div>
                  <p className="text-white font-medium">Timeline View</p>
                  <p className="fi-subtitle">Vista cronológica de eventos</p>
                </div>
                <div className="fi-flex-gap">
                  <span className="fi-text-green text-sm font-medium">Activo</span>
                  <div className="w-12 h-6 bg-green-600 rounded-full relative cursor-pointer">
                    <div className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full"></div>
                  </div>
                </div>
              </div>

              <div className="fi-settings-row">
                <div>
                  <p className="text-white font-medium">Advanced Diarization</p>
                  <p className="fi-subtitle">Separación de voces mejorada</p>
                </div>
                <div className="fi-flex-gap">
                  <span className="text-slate-400 text-sm font-medium">Inactivo</span>
                  <div className="w-12 h-6 bg-slate-600 rounded-full relative cursor-pointer">
                    <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Security & Access */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-lg overflow-hidden">
            <div className="px-6 py-4 bg-slate-900/50 fi-border-bottom">
              <h2 className="fi-title">Seguridad & Acceso</h2>
              <p className="fi-subtitle">Gestión de roles y permisos</p>
            </div>
            <div className="p-6 space-y-4">
              <div className="fi-settings-row-bordered">
                <div>
                  <p className="text-white font-medium">Usuarios Activos</p>
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
                  <p className="text-white font-medium">Roles & Permisos</p>
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
                  <p className="text-white font-medium">Audit Trail</p>
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
          <div className="bg-slate-800/50 border border-slate-700 rounded-lg overflow-hidden">
            <div className="px-6 py-4 bg-slate-900/50 fi-border-bottom">
              <h2 className="fi-title">Gestión de Usuarios & Roles</h2>
              <p className="fi-subtitle">Administración centralizada de permisos RBAC</p>
            </div>
            <div className="p-6 space-y-6">
              {/* Current User Info */}
              <div className="bg-slate-900/50 border border-slate-600 rounded-lg p-4">
                <div className="fi-flex-between mb-3">
                  <h3 className="fi-title-sm">Usuario Actual</h3>
                  {isSuperAdmin && (
                    <span className="px-2 py-1 bg-purple-600 text-white text-xs font-bold rounded">
                      SUPERADMIN
                    </span>
                  )}
                </div>
                <div className="fi-stack-sm">
                  <div className="fi-flex-between text-sm">
                    <span className="text-slate-400">Email:</span>
                    <span className="text-white font-mono">{user?.email}</span>
                  </div>
                  <div className="fi-flex-between text-sm">
                    <span className="text-slate-400">User ID:</span>
                    <span className="text-slate-500 font-mono text-xs truncate max-w-xs">
                      {user?.sub}
                    </span>
                  </div>
                  <div className="flex items-start justify-between text-sm pt-2 fi-border-top">
                    <span className="text-slate-400">Roles:</span>
                    <div className="flex flex-wrap gap-1 justify-end max-w-xs">
                      {roles.length > 0 ? (
                        roles.map(role => (
                          <span
                            key={role}
                            className={`px-2 py-1 ${getRoleBadgeColor(role)} text-white fi-text-xs-medium rounded`}
                          >
                            {getRoleName(role)}
                          </span>
                        ))
                      ) : (
                        <span className="text-slate-500 text-xs">Sin roles asignados</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Roles Definition */}
              <div>
                <h3 className="fi-title-sm mb-3">Roles Disponibles</h3>
                <div className="space-y-2">
                  {Object.entries(ROLES).map(([_key, role]) => (
                    <div
                      key={role}
                      className="fi-list-item"
                    >
                      <div className="fi-flex-gap-md">
                        <span className={`px-3 py-1 ${getRoleBadgeColor(role)} text-white fi-text-xs-medium rounded`}>
                          {getRoleName(role)}
                        </span>
                        <span className="text-slate-400 text-sm font-mono">{role}</span>
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
                <h3 className="fi-title-sm mb-3">Permisos por Rol</h3>
                <div className="bg-slate-900/30 border border-slate-700 rounded-lg p-4 overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="fi-border-bottom">
                        <th className="text-left py-2 px-2 text-slate-400 font-medium">Permiso</th>
                        <th className="text-center py-2 px-2 fi-text-purple font-medium">SUPERADMIN</th>
                        <th className="text-center py-2 px-2 fi-text-success font-medium">CLINICIAN</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-slate-800">
                        <td className="py-2 px-2 fi-text">Gestionar Sistema</td>
                        <td className="text-center">Si</td>
                        <td className="text-center text-slate-600">--</td>
                      </tr>
                      <tr className="border-b border-slate-800">
                        <td className="py-2 px-2 fi-text">Ver Logs</td>
                        <td className="text-center">Si</td>
                        <td className="text-center text-slate-600">--</td>
                      </tr>
                      <tr className="border-b border-slate-800">
                        <td className="py-2 px-2 fi-text">Gestionar Usuarios</td>
                        <td className="text-center">Si</td>
                        <td className="text-center text-slate-600">--</td>
                      </tr>
                      <tr className="border-b border-slate-800">
                        <td className="py-2 px-2 fi-text">Crear Sesion</td>
                        <td className="text-center">Si</td>
                        <td className="text-center">Si</td>
                      </tr>
                      <tr className="border-b border-slate-800">
                        <td className="py-2 px-2 fi-text">Ver Sesion</td>
                        <td className="text-center">Si</td>
                        <td className="text-center">Si</td>
                      </tr>
                      <tr className="border-b border-slate-800">
                        <td className="py-2 px-2 fi-text">Exportar Datos</td>
                        <td className="text-center">Si</td>
                        <td className="text-center">Si</td>
                      </tr>
                      <tr>
                        <td className="py-2 px-2 fi-text">Eliminar Sesion</td>
                        <td className="text-center">Si</td>
                        <td className="text-center text-slate-600">--</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Superadmin Configuration */}
              <div className="bg-purple-900/20 border border-purple-700/30 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-purple-300 mb-2 fi-flex-gap">
                  <Star className="w-4 h-4 fill-current" />
                  Configuración Superadmin
                </h3>
                <p className="text-xs fi-text-purple/80 mb-3">
                  Lista de emails con acceso completo al sistema (configurado via <code className="bg-purple-950/50 px-1 py-0.5 rounded">NEXT_PUBLIC_SUPERADMIN_EMAILS</code>)
                </p>
                <div className="bg-slate-950/50 border border-purple-800/30 rounded p-3">
                  <code className="text-xs text-purple-300 font-mono">
                    NEXT_PUBLIC_SUPERADMIN_EMAILS=bernarduriza@gmail.com,admin@aurity.app
                  </code>
                </div>
                <p className="fi-text-xs-muted mt-2">
                  Nota: Cambios requieren rebuild del frontend (pnpm build)
                </p>
              </div>

              {/* Auth Integration Note */}
              <div className="bg-blue-900/20 border border-blue-700/30 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-blue-300 mb-2">
                   Autenticación JWT
                </h3>
                <p className="text-xs fi-text-primary/80 mb-2">
                  Los roles se asignan al registrar usuarios y se incluyen en el JWT token bajo el claim:
                </p>
                <code className="block bg-slate-950/50 border border-blue-800/30 rounded p-2 text-xs text-blue-300 font-mono">
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
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowRolesModal(false)}>
          <div className="bg-slate-800 rounded-lg max-w-3xl w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-6 fi-border-bottom">
              <h2 className="fi-title-xl">Configurar Roles & Permisos</h2>
              <p className="fi-subtitle mt-1">Configuración RBAC del sistema</p>
            </div>
            <div className="p-6 space-y-4">
              <div className="bg-purple-900/20 border border-purple-700/30 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-purple-300 mb-2"> Gestión de Roles</h3>
                <ol className="text-xs fi-text space-y-3 list-decimal list-inside">
                  <li>
                    <strong className="text-white">Roles disponibles</strong>
                    <div className="ml-5 mt-2 bg-slate-950/50 p-2 rounded text-[10px] font-mono text-slate-400">
                      FI-superadmin, FI-clinician
                    </div>
                  </li>
                  <li>
                    <strong className="text-white">Asignación de roles</strong>
                    <p className="text-slate-400 ml-5 mt-1">Los roles se asignan al registrar usuarios o via el panel de administración de usuarios.</p>
                  </li>
                  <li>
                    <strong className="text-white">JWT Claims</strong>
                    <p className="text-slate-400 ml-5 mt-1">Los roles se incluyen automáticamente en el JWT token bajo el claim &quot;roles&quot;.</p>
                  </li>
                </ol>
              </div>

              <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-4">
                <h3 className="fi-title-sm mb-3">Roles Definidos en AURITY</h3>
                <div className="space-y-2">
                  {Object.entries(ROLES).map(([_key, role]) => (
                    <div key={role} className="fi-flex-between text-xs p-2 bg-slate-800/50 rounded">
                      <div className="fi-flex-gap">
                        <span className={`px-2 py-1 ${getRoleBadgeColor(role)} text-white font-medium rounded`}>
                          {getRoleName(role)}
                        </span>
                        <code className="text-slate-400 font-mono">{role}</code>
                      </div>
                      <span className="text-slate-500">
                        {role === ROLES.SUPERADMIN && 'Full access'}
                        {role === ROLES.CLINICIAN && 'Clinical operations'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-blue-900/20 border border-blue-700/30 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-blue-300 mb-2"> Permisos por Rol</h3>
                <p className="text-xs fi-text-primary/80">
                  Cada rol tiene permisos predefinidos que se verifican automáticamente en cada endpoint del backend.
                  El primer usuario registrado recibe el rol FI-superadmin automáticamente.
                </p>
              </div>
            </div>
            <div className="p-4 fi-border-top flex justify-end gap-2">
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
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowAuditModal(false)}>
          <div className="bg-slate-800 rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-6 fi-border-bottom">
              <h2 className="fi-title-xl">Audit Trail</h2>
              <p className="fi-subtitle mt-1">Registro de auditoría del sistema</p>
            </div>
            <div className="p-6 space-y-4">
              <div className="bg-emerald-900/20 border border-emerald-700/30 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-emerald-300 mb-2">Si Backend Audit Trail Activo</h3>
                <p className="text-xs fi-text mb-3">
                  El backend ya registra todas las operaciones en HDF5:
                </p>
                <ul className="fi-text-xs space-y-2 list-disc list-inside">
                  <li>Operaciones LLM (generate, embed)</li>
                  <li>Exportaciones de datos</li>
                  <li>Búsquedas en corpus</li>
                  <li>Operaciones críticas (delete)</li>
                </ul>
                <div className="mt-3 bg-slate-950/50 p-2 rounded">
                  <code className="text-[10px] fi-text-success">
                    Location: /storage/corpus.h5:/audit_logs
                  </code>
                </div>
              </div>

              <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-4">
                <h3 className="fi-title-sm mb-3">Estructura de Logs</h3>
                <div className="bg-slate-950/50 p-3 rounded">
                  <pre className="text-[10px] text-slate-400 overflow-x-auto">
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

              <div className="bg-yellow-900/20 border border-yellow-700/30 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-yellow-300 mb-2"> UI de Auditoría - En Desarrollo</h3>
                <p className="text-xs text-yellow-400/80 mb-2">
                  Próximamente: Interfaz para visualizar y filtrar logs de auditoría
                </p>
                <ul className="fi-text-xs space-y-1 list-disc list-inside">
                  <li>Timeline de eventos con filtros</li>
                  <li>Búsqueda por usuario, operación, fecha</li>
                  <li>Export de logs (CSV, JSON)</li>
                  <li>Alertas en tiempo real</li>
                  <li>Estadísticas de uso por usuario</li>
                </ul>
              </div>

              <div className="bg-blue-900/20 border border-blue-700/30 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-blue-300 mb-2"> Inspección Manual</h3>
                <p className="text-xs fi-text mb-2">
                  Puedes inspeccionar los logs manualmente usando:
                </p>
                <div className="bg-slate-950/50 p-2 rounded">
                  <code className="text-[10px] fi-text-primary">
                    python backend/tools/inspect_corpus.py --audit-logs
                  </code>
                </div>
              </div>
            </div>
            <div className="p-4 fi-border-top flex justify-end">
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
