'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { ROLES, getRoleName, getRoleBadgeColor, type Role } from '@aurity-standalone/hooks/useRBAC';
import { showError, showSuccess } from '@/lib/swal';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('InviteUser');

interface InviteUserModalProps {
  onClose: () => void;
  onInvite: () => void;
}

export function InviteUserModal({ onClose, onInvite }: InviteUserModalProps) {
  useAuth(); // Ensure auth context is available
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [selectedRole, setSelectedRole] = useState<Role>(ROLES.CLINICIAN);
  const [sending, setSending] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSending(true);

    try {
      const { adminApi } = await import('@/lib/api/admin');
      await adminApi.createUser({
        email,
        name: name || undefined,
        password: undefined,
      });

      await showSuccess('Usuario creado', `Invitación enviada a ${email}`);
      onInvite();
      onClose();
    } catch (error) {
      log.error('Failed to invite user', { error: String(error) });
      await showError('Error', 'No se pudo crear el usuario');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fi-modal-backdrop z-[60]" onClick={onClose}>
      <div className="fi-modal-sm p-6" onClick={(e) => e.stopPropagation()}>
        <h3 className="fi-title mb-4">Invitar Usuario</h3>

        <form onSubmit={handleSubmit} className="fi-stack-lg">
          <div>
            <label className="fi-label">Email *</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="usuario@ejemplo.com"
              className="fi-input-blue"
            />
          </div>

          <div>
            <label className="fi-label">Nombre (opcional)</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Juan Pérez"
              className="fi-input-blue"
            />
          </div>

          <div>
            <label className="fi-label">Rol</label>
            <div className="fi-stack-sm">
              {Object.values(ROLES).filter(r => r !== ROLES.SUPERADMIN).map(role => (
                <label key={role} className="admin-invite-role-label">
                  <input
                    type="radio"
                    name="user-role"
                    checked={selectedRole === role}
                    onChange={() => setSelectedRole(role)}
                    className="admin-invite-radio"
                  />
                  <span className={`admin-role-badge-sm ${getRoleBadgeColor(role)}`}>
                    {getRoleName(role)}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="admin-invite-actions">
            <Button type="button" onClick={onClose} variant="secondary" fullWidth>
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={sending || !email}
              variant="primary"
              fullWidth
              loading={sending}
            >
              Enviar Invitación
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
