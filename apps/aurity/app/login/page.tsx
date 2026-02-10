'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/auth/AuthProvider';
import { Loader2 } from 'lucide-react';
import Link from 'next/link';

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Already logged in — redirect
  if (isAuthenticated && !authLoading) {
    router.replace('/chat');
    return null;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      router.push('/chat');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-login-wrapper">
      <div className="auth-login-card">
        <h1 className="auth-login-title">AURITY</h1>
        <p className="auth-login-subtitle">Inicia sesion para continuar</p>

        <form onSubmit={handleSubmit} className="auth-login-form">
          <div>
            <label htmlFor="email" className="auth-login-label">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="layout-auth-input"
              placeholder="tu@correo.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="auth-login-label">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="layout-auth-input"
              placeholder="********"
            />
          </div>

          {error && (
            <p className="auth-login-error">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="layout-auth-submit"
          >
            {loading && <Loader2 className="auth-login-icon-spin" />}
            {loading ? 'Entrando...' : 'Entrar'}
          </button>
        </form>

        <p className="auth-login-footer">
          No tienes cuenta?{' '}
          <Link href="/register" className="auth-login-link">
            Registrate
          </Link>
        </p>
      </div>
    </div>
  );
}
