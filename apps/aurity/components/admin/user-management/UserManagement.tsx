'use client';

/**
 * UserManagement Component
 * Integrated user administration without leaving AURITY
 */

import { useState, useEffect, useCallback } from 'react';
import { Plus, Building2, X, Eye, Ban, Check, RefreshCw, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { useRBAC, ROLES, getRoleName, getRoleBadgeColor, type Role } from '@aurity-standalone/hooks/useRBAC';
import { toastError, toastSuccess } from '@/lib/swal';
import {
  fetchClinics,
  adminUnassignUserFromClinic,
  adminGetUserClinicInfo,
  type Clinic,
} from '@/lib/api/clinics';

import type { User, UserManagementProps } from './types';
import { InviteUserModal, UserActivityModal, ClinicAssignmentModal } from './modals';

export function UserManagement({ onClose, asPage = false }: UserManagementProps) {
  const { getAccessTokenSilently } = useAuth();
  useRBAC(); // Initialize RBAC context
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState<Role | 'all'>('all');
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [showClinicModal, setShowClinicModal] = useState(false);
  const [clinicAssignUser, setClinicAssignUser] = useState<User | null>(null);
  const [, setLoadingClinicInfo] = useState<string | null>(null);

  const loadClinics = useCallback(async () => {
    try {
      const clinicList = await fetchClinics(true);
      setClinics(clinicList);
    } catch (error) {
      console.error('Failed to load clinics:', error);
    }
  }, []);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const { adminApi } = await import('@/lib/api/admin');
      const data = await adminApi.getUsers({ per_page: 100 });

      const mappedUsers: User[] = data.users.map((u: any) => ({
        user_id: u.user_id,
        email: u.email,
        name: u.name,
        picture: u.picture,
        created_at: u.created_at,
        last_login: u.last_login,
        logins_count: u.logins_count,
        roles: u.roles || [],
        blocked: u.blocked,
      }));

      const usersWithClinicInfo = await Promise.all(
        mappedUsers.map(async (user) => {
          try {
            const clinicInfo = await adminGetUserClinicInfo(user.user_id);
            return { ...user, clinicInfo };
          } catch {
            return { ...user, clinicInfo: undefined };
          }
        })
      );

      setUsers(usersWithClinicInfo);
    } catch (error) {
      console.error('Failed to load users:', error);
      setUsers([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const initAndLoad = async () => {
      try {
        const token = await getAccessTokenSilently({
          authorizationParams: {
            audience: process.env.NEXT_PUBLIC_AUTH0_AUDIENCE || 'https://app.aurity.io',
          }
        });
        const { setAdminToken } = await import('@/lib/api/admin');
        setAdminToken(token);

        loadUsers();
        loadClinics();
      } catch (error) {
        console.error('Failed to get auth token:', error);
        setLoading(false);
      }
    };

    initAndLoad();
  }, [getAccessTokenSilently, loadUsers, loadClinics]);

  const loadUserClinicInfo = async (user: User) => {
    setLoadingClinicInfo(user.user_id);
    try {
      const clinicInfo = await adminGetUserClinicInfo(user.user_id);
      setUsers(prev => prev.map(u => u.user_id === user.user_id ? { ...u, clinicInfo } : u));
    } catch (error) {
      console.error('Failed to load clinic info:', error);
    } finally {
      setLoadingClinicInfo(null);
    }
  };

  const handleOpenClinicModal = async (user: User) => {
    if (!user.clinicInfo) await loadUserClinicInfo(user);
    setClinicAssignUser(user);
    setShowClinicModal(true);
  };

  const handleUnassignFromClinic = async (user: User) => {
    try {
      await adminUnassignUserFromClinic(user.user_id);
      setUsers(prev => prev.map(u =>
        u.user_id === user.user_id
          ? { ...u, clinicInfo: { ...u.clinicInfo!, is_linked: false, clinic_id: null, clinic_name: null } }
          : u
      ));
      toastSuccess('Usuario removido de clínica');
    } catch {
      toastError('Error al remover usuario de clínica');
    }
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.name?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = roleFilter === 'all' || user.roles.includes(roleFilter);
    return matchesSearch && matchesRole;
  });

  const handleRoleToggle = async (user: User, role: Role) => {
    try {
      const hasRole = user.roles.includes(role);
      const updatedRoles = hasRole ? user.roles.filter(r => r !== role) : [...user.roles, role];
      const { adminApi } = await import('@/lib/api/admin');
      await adminApi.updateUserRoles(user.user_id, updatedRoles);
      setUsers(users.map(u => u.user_id === user.user_id ? { ...u, roles: updatedRoles } : u));
      toastSuccess('Roles actualizados correctamente');
    } catch {
      toastError('Error al actualizar roles');
    }
  };

  const handleBlockToggle = async (user: User) => {
    try {
      const newBlockedState = !user.blocked;
      const { adminApi } = await import('@/lib/api/admin');
      await adminApi.blockUser(user.user_id, newBlockedState);
      setUsers(users.map(u => u.user_id === user.user_id ? { ...u, blocked: newBlockedState } : u));
      toastSuccess(newBlockedState ? 'Usuario bloqueado' : 'Usuario desbloqueado');
    } catch {
      toastError('Error al bloquear/desbloquear usuario');
    }
  };

  const wrapperClass = asPage
    ? "min-h-screen bg-slate-950"
    : "fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4";

  const containerClass = asPage
    ? "bg-slate-900 min-h-screen flex flex-col"
    : "bg-slate-800 rounded-lg max-w-6xl w-full max-h-[90vh] flex flex-col";

  return (
    <div className={wrapperClass} onClick={asPage ? undefined : onClose}>
      <div className={containerClass} onClick={asPage ? undefined : (e) => e.stopPropagation()}>
        {/* Header */}
        <div className="p-6 fi-border-bottom">
          <div className="fi-flex-between">
            <div>
              <h2 className="fi-title-xl">Gestión de Usuarios</h2>
              <p className="fi-subtitle mt-1">Administración integrada · Roles y Clínicas</p>
            </div>
            {!asPage && (
              <button onClick={onClose} className="fi-btn-close">
                <X className="fi-icon-lg" />
              </button>
            )}
          </div>

          <div className="mt-4 flex gap-3">
            <div className="flex-1 relative">
              <input
                type="text"
                placeholder="Buscar por email o nombre..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="fi-input-blue"
              />
              <Search className="absolute right-3 top-2.5 fi-icon-md fi-icon-slate" />
            </div>

            <Select value={roleFilter} onValueChange={(val) => setRoleFilter(val as Role | 'all')}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Todos los roles" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los roles</SelectItem>
                {Object.values(ROLES).map(role => (
                  <SelectItem key={role} value={role}>{getRoleName(role)}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button onClick={() => setShowInviteModal(true)} variant="primary" icon={Plus}>
              Invitar Usuario
            </Button>
          </div>
        </div>

        {/* User List */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin h-12 w-12 border-4 border-blue-400 border-t-transparent rounded-full" />
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="text-center text-slate-500 py-12">No se encontraron usuarios</div>
          ) : (
            <div className="space-y-3">
              {filteredUsers.map(user => (
                <div
                  key={user.user_id}
                  className={`bg-slate-900/50 border rounded-lg p-4 hover:border-slate-600 transition-colors ${
                    user.blocked ? 'border-red-900/50 opacity-60' : 'border-slate-700'
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0">
                      {user.picture ? (
                        <img src={user.picture} alt={user.name} className="w-12 h-12 rounded-full" />
                      ) : (
                        <div className="fi-avatar-md">
                          {user.name?.[0] || user.email[0].toUpperCase()}
                        </div>
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className="text-white font-medium flex items-center gap-2">
                            {user.name || user.email}
                            {user.blocked && (
                              <span className="px-2 py-0.5 bg-red-900/30 border border-red-700 fi-text-error text-xs rounded">
                                Bloqueado
                              </span>
                            )}
                          </h3>
                          <p className="fi-subtitle font-mono">{user.email}</p>
                        </div>

                        <div className="flex gap-2">
                          <Button onClick={() => handleOpenClinicModal(user)} variant="blue" size="sm" icon={Building2}>
                            Clínica
                          </Button>
                          <Button onClick={() => setSelectedUser(user)} variant="secondary" size="sm" icon={Eye}>
                            Ver Actividad
                          </Button>
                          <Button
                            onClick={() => handleBlockToggle(user)}
                            variant={user.blocked ? 'success' : 'danger'}
                            size="sm"
                            icon={user.blocked ? Check : Ban}
                          >
                            {user.blocked ? 'Desbloquear' : 'Bloquear'}
                          </Button>
                        </div>
                      </div>

                      {user.clinicInfo?.is_linked && (
                        <div className="flex items-center gap-2 mb-3">
                          <span className="px-2 py-1 bg-blue-900/30 border border-blue-700/50 text-blue-300 text-xs rounded flex items-center gap-1">
                            <Building2 className="w-3 h-3" />
                            {user.clinicInfo.clinic_name} ({user.clinicInfo.clinic_role})
                          </span>
                          <Button
                            onClick={() => handleUnassignFromClinic(user)}
                            variant="ghost"
                            size="xs"
                            className="fi-text-error hover:text-red-300"
                          >
                            Remover
                          </Button>
                        </div>
                      )}

                      <div className="flex gap-4 fi-text-xs-muted mb-3">
                        <span>Creado: {new Date(user.created_at).toLocaleDateString('es-MX')}</span>
                        {user.last_login && (
                          <span>Último acceso: {new Date(user.last_login).toLocaleDateString('es-MX')}</span>
                        )}
                        <span>Logins: {user.logins_count || 0}</span>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {Object.values(ROLES).map(role => {
                          const hasRole = user.roles.includes(role);
                          return (
                            <button
                              key={role}
                              onClick={() => handleRoleToggle(user, role)}
                              className={hasRole
                                ? `fi-role-toggle-active ${getRoleBadgeColor(role)}`
                                : 'fi-role-toggle'
                              }
                            >
                              {hasRole && <><Check className="w-3 h-3 inline mr-1" strokeWidth={1.5} aria-hidden="true" /></>}
                              {getRoleName(role)}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 fi-border-top bg-slate-900/50">
          <div className="flex items-center justify-between fi-subtitle">
            <span>
              {filteredUsers.length} usuario{filteredUsers.length !== 1 ? 's' : ''}
              {searchTerm || roleFilter !== 'all' ? ` (filtrado de ${users.length})` : ''}
            </span>
            <Button onClick={loadUsers} variant="ghost" size="sm" icon={RefreshCw}>
              Recargar
            </Button>
          </div>
        </div>
      </div>

      {showInviteModal && (
        <InviteUserModal onClose={() => setShowInviteModal(false)} onInvite={loadUsers} />
      )}

      {selectedUser && (
        <UserActivityModal user={selectedUser} onClose={() => setSelectedUser(null)} />
      )}

      {showClinicModal && clinicAssignUser && (
        <ClinicAssignmentModal
          user={clinicAssignUser}
          clinics={clinics}
          currentClinicInfo={clinicAssignUser.clinicInfo}
          onClose={() => { setShowClinicModal(false); setClinicAssignUser(null); }}
          onAssigned={(clinicInfo) => {
            setUsers(prev => prev.map(u => u.user_id === clinicAssignUser.user_id ? { ...u, clinicInfo } : u));
            setShowClinicModal(false);
            setClinicAssignUser(null);
          }}
        />
      )}
    </div>
  );
}

export default UserManagement;
