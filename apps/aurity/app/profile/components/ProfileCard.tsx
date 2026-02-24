'use client';

/**
 * Profile card with avatar, user info, and metadata.
 */

import Image from 'next/image';
import { CheckCircle2 } from 'lucide-react';
import type { ProfileUser } from '../types';

interface ProfileCardProps {
  user: ProfileUser | undefined;
}

export function ProfileCard({ user }: ProfileCardProps) {
  return (
    <div className="prof-card">
      {/* Header with Avatar */}
      <div className="prof-card-header">
        <div className="prof-avatar-row">
          {user?.picture ? (
            <img
              src={user.picture}
              alt={user.name || 'User'}
              className="prof-avatar-img"
            />
          ) : (
            <div className="fi-avatar-lg prof-avatar-fallback">
              <Image
                src="/logo.svg"
                alt="Aurity Logo"
                width={64}
                height={64}
                className="prof-avatar-logo"
              />
            </div>
          )}
          <div>
            <h2 className="fi-title-2xl">{user?.name || 'Usuario'}</h2>
            <p className="prof-email">{user?.email}</p>
            {user?.email_verified && (
              <div className="prof-verified-row">
                <CheckCircle2 className="fi-icon-sm prof-verified-icon" />
                <span className="prof-verified-text fi-text-green">Email verificado</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Profile Information */}
      <div className="prof-info-content">
        <AccountInfo user={user} />
        <UserMetadata user={user} />
      </div>
    </div>
  );
}

function AccountInfo({ user }: { user: ProfileUser | undefined }) {
  const fields = [
    { label: 'Nombre', value: user?.name },
    { label: 'Email', value: user?.email },
    { label: 'Nickname', value: user?.nickname },
    {
      label: 'Última actualización',
      value: user?.updated_at
        ? new Date(user.updated_at).toLocaleDateString('es-MX')
        : undefined,
    },
  ];

  return (
    <div>
      <h3 className="fi-title prof-info-title">Información de la Cuenta</h3>
      <div className="fi-stack-md">
        {fields.map(({ label, value }) => (
          <div key={label} className="prof-info-row fi-border-bottom">
            <span className="prof-label">{label}</span>
            <span className="prof-value">{value || 'No disponible'}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function UserMetadata({ user }: { user: ProfileUser | undefined }) {
  if (!user || Object.keys(user).length === 0) return null;

  return (
    <div>
      <h3 className="fi-title prof-info-title">Datos Adicionales</h3>
      <div className="prof-metadata-block">
        <pre className="fi-text-xs prof-metadata-pre">
          {JSON.stringify(user, null, 2)}
        </pre>
      </div>
    </div>
  );
}
