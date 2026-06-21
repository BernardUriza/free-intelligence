'use client';

/**
 * AuthGate — gates the app behind Auth0 login in auth0 mode; passthrough in
 * bearer mode (the legacy paste-token flow stays inside Og118AgentChat).
 *
 * Open self-serve signups: the login button goes to Auth0 Universal Login, which
 * offers sign-up. Ownership (per-account corpus isolation) is enforced server-side
 * (PROJ-ACCOUNT-1), so open signups are safe.
 */

import { useAuth0 } from '@auth0/auth0-react';

import { isAuth0Mode } from '@/lib/authMode';

const screen: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '1rem',
  minHeight: '100dvh',
  textAlign: 'center',
  padding: '2rem',
};

const button: React.CSSProperties = {
  padding: '0.6rem 1.4rem',
  borderRadius: 9999,
  border: 'none',
  background: '#34d399',
  color: '#0a0f1e',
  fontWeight: 600,
  cursor: 'pointer',
};

function Auth0Gate({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated, loginWithRedirect, logout, user } = useAuth0();

  if (isLoading) {
    return <div style={screen}>Cargando…</div>;
  }
  if (!isAuthenticated) {
    return (
      <div style={screen}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 700 }}>og118</h1>
        <p style={{ opacity: 0.7 }}>Inicia sesión para continuar.</p>
        <button style={button} onClick={() => void loginWithRedirect()}>
          Iniciar sesión
        </button>
      </div>
    );
  }
  return (
    <>
      {children}
      <button
        type="button"
        aria-label="Cerrar sesión"
        onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
        style={{
          position: 'fixed',
          top: 12,
          right: 12,
          zIndex: 50,
          fontSize: '0.72rem',
          padding: '0.3rem 0.7rem',
          borderRadius: 9999,
          border: '1px solid rgba(255,255,255,0.15)',
          background: 'rgba(255,255,255,0.06)',
          color: '#cbd5e1',
          cursor: 'pointer',
        }}
      >
        Salir{user?.email ? ` · ${user.email}` : ''}
      </button>
    </>
  );
}

export function AuthGate({ children }: { children: React.ReactNode }) {
  if (!isAuth0Mode) return <>{children}</>;
  return <Auth0Gate>{children}</Auth0Gate>;
}
