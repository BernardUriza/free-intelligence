'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/auth/AuthProvider';
import { Loader2 } from 'lucide-react';
import Link from 'next/link';

export default function RegisterPage() {
  const router = useRouter();
  const { register, isAuthenticated, isLoading: authLoading } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (isAuthenticated && !authLoading) {
    router.replace('/chat');
    return null;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    setLoading(true);
    try {
      await register(email, password, name);
      router.push('/chat');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-register-wrapper">
      <div className="auth-register-card">
        <h1 className="auth-register-title">AURITY</h1>
        <p className="auth-register-subtitle">Crea tu cuenta</p>

        <form onSubmit={handleSubmit} className="auth-register-form">
          <div>
            <label htmlFor="name" className="auth-register-label">
              Nombre
            </label>
            <input
              id="name"
              type="text"
              required
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="layout-auth-input"
              placeholder="Dr. Juan Perez"
            />
          </div>

          <div>
            <label htmlFor="email" className="auth-register-label">
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
            <label htmlFor="password" className="auth-register-label">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              autoComplete="new-password"
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="layout-auth-input"
              placeholder="Minimo 8 caracteres"
            />
          </div>

          {error && (
            <p className="auth-register-error">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="layout-auth-submit"
          >
            {loading && <Loader2 className="auth-register-icon-spin" />}
            {loading ? 'Registrando...' : 'Crear cuenta'}
          </button>
        </form>

        <p className="auth-register-footer">
          Ya tienes cuenta?{' '}
          <Link href="/login" className="auth-register-link">
            Inicia sesion
          </Link>
        </p>
      </div>
    </div>
  );
}
