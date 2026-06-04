'use client';

import { useState, useEffect, FormEvent, KeyboardEvent } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { useAuth } from '@/components/auth/AuthProvider';
import { NeuralNetworkCanvas } from '@/components/background/NeuralNetworkCanvas';
import { Loader2, Eye, EyeOff, AlertTriangle } from 'lucide-react';
import Link from 'next/link';

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [capsLock, setCapsLock] = useState(false);

  // Already logged in — redirect (side effect, never during render).
  // Calling router.replace() in the render body triggers a setState on Router
  // while LoginPage renders → React error. It belongs in an effect.
  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      router.replace('/chat');
    }
  }, [isAuthenticated, authLoading, router]);

  if (isAuthenticated && !authLoading) {
    return null; // render nothing while the effect performs the redirect
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

  const handlePasswordKeyEvent = (e: KeyboardEvent<HTMLInputElement>) => {
    setCapsLock(e.getModifierState('CapsLock'));
  };

  return (
    <div className="auth-login-wrapper">
      <NeuralNetworkCanvas opacity={0.25} />
      <div className="auth-login-card">
        <div className="auth-login-logo-wrapper">
          <Image
            src="/logos/aurity-logo-light.png"
            alt="Aurity"
            width={180}
            height={45}
            className="w-auto h-auto"
            priority
          />
        </div>
        <p className="auth-login-subtitle">Inicia sesión para continuar</p>

        <form onSubmit={handleSubmit} className="auth-login-form">
          <div>
            <label htmlFor="email" className="auth-login-label">
              Correo electrónico
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
              Contraseña
            </label>
            <div className="auth-login-password-wrapper">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyUp={handlePasswordKeyEvent}
                onKeyDown={handlePasswordKeyEvent}
                className="layout-auth-input auth-login-password-input"
                placeholder="********"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="auth-login-password-toggle"
                tabIndex={-1}
                aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {capsLock && (
              <p className="auth-login-capslock">
                <AlertTriangle size={14} />
                Caps Lock activado
              </p>
            )}
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
            Regístrate
          </Link>
        </p>
      </div>
    </div>
  );
}
