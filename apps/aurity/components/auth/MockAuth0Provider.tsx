'use client';

/**
 * MockAuth0Provider - Development Authentication Provider
 * 
 * Provides mock authentication context for local development
 * when real Auth0 credentials are not available or when using mock
 * authentication for UI testing.
 */

import { createContext, useContext, ReactNode, useState, useEffect, ReactElement } from 'react';

// Development-only logging utility
const devLog = (message: string, ...args: any[]) => {
  if (process.env.NODE_ENV === 'development') {
    console.log(message, ...args);
  }
};

// Define el tipo para el contexto de autenticación (compatible con Auth0 SDK)
interface Auth0ContextType {
  isLoading: boolean;
  isAuthenticated: boolean;
  user: any;
  error?: Error;  // Compatibilidad con Auth0 SDK
  loginWithRedirect: (options?: any) => Promise<void>;
  logout: (options?: LogoutOptions) => Promise<void>;
  getIdTokenClaims: () => Promise<any>;
  getAccessTokenSilently: (options?: any) => Promise<string>;
}

// Match Auth0 SDK logout options
interface LogoutOptions {
  clientId?: string;
  logoutParams?: {
    returnTo?: string;
    federated?: boolean;
  };
  openUrl?: (url: string) => void | Promise<void>;
}

// Creamos el contexto de Auth0
const Auth0Context = createContext<Auth0ContextType | undefined>(undefined);

// Usuario simulado para desarrollo
const MOCK_USER = {
  name: 'Dr. Médico de Prueba',
  email: 'medico@clinic.local',
  sub: 'auth0|dev-user-12345',
  picture: 'https://placehold.co/40x40/3b82f6/FFFFFF?text=MD',
  nickname: 'dr_prueba',
  updated_at: new Date().toISOString(),
  email_verified: true,
};

// Propiedades para el proveedor
interface MockAuth0ProviderProps {
  children: ReactNode;
}

export function MockAuth0Provider({ children }: MockAuth0ProviderProps): ReactElement {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<any>(null);

  // Check for existing session in localStorage (persistent mock auth)
  useEffect(() => {
    const checkAuth = async () => {
      // Simulate auth check delay
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // Check if user was previously authenticated (persisted in localStorage)
      const savedAuth = typeof window !== 'undefined' 
        ? localStorage.getItem('@@mock_auth_user@@')
        : null;

      if (savedAuth) {
        try {
          const userData = JSON.parse(savedAuth);
          devLog('[MockAuth0] Restoring session from localStorage:', userData.email);
          setIsAuthenticated(true);
          setUser(userData);
        } catch {
          devLog('[MockAuth0] Failed to restore session, starting logged out');
          localStorage.removeItem('@@mock_auth_user@@');
        }
      } else {
        devLog('[MockAuth0] No saved session, starting logged out');
      }
      
      setIsLoading(false);

      // If running in desktop offline mode, auto-login the mock user for better UX
      if (process.env.NEXT_PUBLIC_DESKTOP_OFFLINE === 'true') {
        devLog('[MockAuth0] Desktop offline mode detected, auto-login mock user');
        setIsAuthenticated(true);
        setUser(MOCK_USER);
        if (typeof window !== 'undefined') {
          localStorage.setItem('@@mock_auth_user@@', JSON.stringify(MOCK_USER));
        }
      }
    };

    checkAuth();
  }, []);

  // Funciones de autenticación simuladas (compatibles con Auth0 SDK)
  const loginWithRedirect = async (options?: any): Promise<void> => {
    devLog('[MockAuth0] Simulating login...', options);
    // Simulate async auth flow
    await new Promise(resolve => setTimeout(resolve, 100));
    setIsAuthenticated(true);
    setUser(MOCK_USER);
    
    // Persist session in localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem('@@mock_auth_user@@', JSON.stringify(MOCK_USER));
      devLog('[MockAuth0] Session saved to localStorage');
    }
  };

  const logout = async (options?: LogoutOptions): Promise<void> => {
    devLog('[MockAuth0] Simulating logout...', options);
    // Simulate async logout
    await new Promise(resolve => setTimeout(resolve, 50));
    setIsAuthenticated(false);
    setUser(null);

    // Clear ALL auth-related data from localStorage
    if (typeof window !== 'undefined') {
      // Remove mock auth session
      localStorage.removeItem('@@mock_auth_user@@');
      
      // Clear Auth0 SDK cache keys (for compatibility)
      Object.keys(localStorage).forEach(key => {
        if (key.startsWith('@@auth0spajs@@')) {
          localStorage.removeItem(key);
          devLog('[MockAuth0] Cleared localStorage key:', key);
        }
      });
      
      devLog('[MockAuth0] All auth data cleared from localStorage');
    }

    // Handle returnTo redirect (match real SDK behavior)
    if (options?.logoutParams?.returnTo && typeof window !== 'undefined') {
      devLog('[MockAuth0] Redirecting to:', options.logoutParams.returnTo);
      window.location.href = options.logoutParams.returnTo;
    }
  };

  const getIdTokenClaims = async () => {
    // Simulamos un JWT con la información del usuario
    return {
      __raw: 'mocked-id-token-for-development',
      name: MOCK_USER.name,
      email: MOCK_USER.email,
      sub: MOCK_USER.sub,
      exp: Math.floor(Date.now() / 1000) + (15 * 60), // Expira en 15 minutos
    };
  };

  const getAccessTokenSilently = async (options?: any): Promise<string> => {
    devLog('[MockAuth0] Getting access token silently', options);
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 50));

    if (!isAuthenticated) {
      throw new Error('User is not authenticated');
    }

    return 'mocked-access-token-for-development';
  };

  const contextValue: Auth0ContextType = {
    isLoading,
    isAuthenticated,
    user,
    loginWithRedirect,
    logout,
    getIdTokenClaims,
    getAccessTokenSilently,
  };

  return (
    <Auth0Context.Provider value={contextValue}>
      {children}
    </Auth0Context.Provider>
  );
}

// Hook para usar el contexto de Auth0
export const useAuth0 = (): Auth0ContextType => {
  const context = useContext(Auth0Context);
  if (context === undefined) {
    throw new Error('useAuth0 must be used within an Auth0Provider');
  }
  return context;
};