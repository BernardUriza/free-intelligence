'use client';

/**
 * AuthGate — gates the app behind Auth0 login in auth0 mode; passthrough in
 * bearer mode (the legacy paste-token flow stays inside Og118AgentChat).
 *
 * Open self-serve signups: the login button goes to Auth0 Universal Login, which
 * offers sign-up. Ownership (per-account corpus isolation) is enforced server-side
 * (PROJ-ACCOUNT-1), so open signups are safe.
 *
 * Styles are inlined at the JSX site on purpose: a shared `React.CSSProperties`
 * const pins one csstype version, and the monorepo's mixed csstype (3.1.3/3.2.3,
 * the hoisting lottery — see react-type-resolution.md) makes that const fail the
 * build on a fresh install. Inline literals are checked against the local csstype.
 */

import { useAuth0 } from '@auth0/auth0-react';

import { isAuth0Mode } from '@/lib/authMode';

function Screen({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '1rem',
        minHeight: '100dvh',
        textAlign: 'center',
        padding: '2rem',
      }}
    >
      {children}
    </div>
  );
}

function Auth0Gate({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated, loginWithRedirect } = useAuth0();

  if (isLoading) {
    return <Screen>Cargando…</Screen>;
  }
  if (!isAuthenticated) {
    return (
      <Screen>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 700 }}>og118</h1>
        <p style={{ opacity: 0.7 }}>Inicia sesión para continuar.</p>
        <button
          onClick={() => void loginWithRedirect()}
          style={{
            padding: '0.6rem 1.4rem',
            borderRadius: 9999,
            border: 'none',
            background: '#34d399',
            color: '#0a0f1e',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Iniciar sesión
        </button>
      </Screen>
    );
  }
  return <>{children}</>;
}

/**
 * The signed-in account line + sign-out, rendered where the layout gives it a
 * home (the sidebar footer) instead of the old `position: fixed` pill that
 * floated over the conversation on every viewport.
 */
function Auth0SignOut() {
  const { isAuthenticated, logout, user } = useAuth0();
  if (!isAuthenticated) return null;
  return (
    <button
      type="button"
      aria-label="Cerrar sesión"
      onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
      style={{
        display: 'block',
        maxWidth: '100%',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
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
  );
}

export function SignOutButton() {
  if (!isAuth0Mode) return null;
  return <Auth0SignOut />;
}

export function AuthGate({ children }: { children: React.ReactNode }) {
  if (!isAuth0Mode) return <>{children}</>;
  return <Auth0Gate>{children}</Auth0Gate>;
}
