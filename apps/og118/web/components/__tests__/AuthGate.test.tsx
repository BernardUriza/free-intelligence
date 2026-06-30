import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';

import { getToken } from '@/lib/og118Token';

// Mutable Auth0 mock — each test sets the fields it needs before rendering.
const mockAuth = {
  isLoading: false,
  isAuthenticated: false,
  loginWithRedirect: vi.fn(),
  logout: vi.fn(),
  getAccessTokenSilently: vi.fn(async () => 'jwt-from-auth0'),
  user: undefined as { email?: string } | undefined,
};

vi.mock('@auth0/auth0-react', () => ({
  useAuth0: () => mockAuth,
  Auth0Provider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

beforeEach(() => {
  localStorage.clear();
  Object.assign(mockAuth, { isLoading: false, isAuthenticated: false, user: undefined });
  mockAuth.loginWithRedirect.mockClear();
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

async function load(mode: 'bearer' | 'auth0', mod: 'AuthGate' | 'Auth0Wrapper') {
  vi.stubEnv('NEXT_PUBLIC_OG118_AUTH_MODE', mode);
  vi.resetModules();
  // Explicit static imports so vite's dynamic-import-vars can analyze them, and so
  // each module's own export type resolves (no union-index).
  if (mod === 'AuthGate') return (await import('../AuthGate')).AuthGate;
  return (await import('../Auth0Wrapper')).Auth0Wrapper;
}

describe('AuthGate', () => {
  it('bearer mode: passthrough — renders children, no login screen', async () => {
    const AuthGate = await load('bearer', 'AuthGate');
    render(
      <AuthGate>
        <div>chat-app</div>
      </AuthGate>,
    );
    expect(screen.getByText('chat-app')).toBeInTheDocument();
    expect(screen.queryByText('Iniciar sesión')).toBeNull();
  });

  it('auth0 mode, unauthenticated: shows the login button', async () => {
    mockAuth.isAuthenticated = false;
    const AuthGate = await load('auth0', 'AuthGate');
    render(
      <AuthGate>
        <div>chat-app</div>
      </AuthGate>,
    );
    expect(screen.getByText('Iniciar sesión')).toBeInTheDocument();
    expect(screen.queryByText('chat-app')).toBeNull();
  });

  it('auth0 mode, authenticated: renders children + a logout affordance', async () => {
    mockAuth.isAuthenticated = true;
    mockAuth.user = { email: 'mama@papeleria.mx' };
    const AuthGate = await load('auth0', 'AuthGate');
    render(
      <AuthGate>
        <div>chat-app</div>
      </AuthGate>,
    );
    expect(screen.getByText('chat-app')).toBeInTheDocument();
    expect(screen.getByLabelText('Cerrar sesión')).toBeInTheDocument();
  });
});

describe('Auth0Wrapper token sync', () => {
  it('auth0 mode, authenticated: mirrors the Auth0 access token into localStorage', async () => {
    mockAuth.isAuthenticated = true;
    const Auth0Wrapper = await load('auth0', 'Auth0Wrapper');
    render(
      <Auth0Wrapper>
        <div>chat-app</div>
      </Auth0Wrapper>,
    );
    await waitFor(() => expect(getToken()).toBe('jwt-from-auth0'));
  });

  it('bearer mode: passthrough, does not touch the token', async () => {
    const Auth0Wrapper = await load('bearer', 'Auth0Wrapper');
    render(
      <Auth0Wrapper>
        <div>chat-app</div>
      </Auth0Wrapper>,
    );
    expect(screen.getByText('chat-app')).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });
});
