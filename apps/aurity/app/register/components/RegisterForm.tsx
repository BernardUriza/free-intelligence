'use client';

/**
 * Registration form UI — name, email, password fields with validation feedback.
 */

import { type FormEvent, type KeyboardEvent, useState } from 'react';
import Image from 'next/image';
import { Loader2, Eye, EyeOff, AlertTriangle } from 'lucide-react';
import Link from 'next/link';
import { NeuralNetworkCanvas } from '@/components/background/NeuralNetworkCanvas';

interface RegisterFormProps {
  name: string;
  email: string;
  password: string;
  error: string;
  submitting: boolean;
  onNameChange: (value: string) => void;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onSubmit: (e: FormEvent) => void;
}

export function RegisterForm({
  name,
  email,
  password,
  error,
  submitting,
  onNameChange,
  onEmailChange,
  onPasswordChange,
  onSubmit,
}: RegisterFormProps) {
  const [showPassword, setShowPassword] = useState(false);
  const [capsLock, setCapsLock] = useState(false);

  const handlePasswordKeyEvent = (e: KeyboardEvent<HTMLInputElement>) => {
    setCapsLock(e.getModifierState('CapsLock'));
  };

  return (
    <div className="auth-register-wrapper">
      <NeuralNetworkCanvas opacity={0.25} />
      <div className="auth-register-card">
        <div className="auth-register-logo-wrapper">
          <Image
            src="/logos/aurity-logo-light.png"
            alt="Aurity"
            width={180}
            height={45}
            className="w-auto h-auto"
            priority
          />
        </div>
        <p className="auth-register-subtitle">Crea tu cuenta</p>

        <form onSubmit={onSubmit} className="auth-register-form" noValidate>
          <div>
            <label htmlFor="name" className="auth-register-label">
              Nombre completo
            </label>
            <input
              id="name"
              type="text"
              required
              autoComplete="name"
              value={name}
              onChange={(e) => onNameChange(e.target.value)}
              className="layout-auth-input"
              placeholder="Dr. Juan Perez"
            />
          </div>

          <div>
            <label htmlFor="email" className="auth-register-label">
              Correo electrónico
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => onEmailChange(e.target.value)}
              className="layout-auth-input"
              placeholder="tu@correo.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="auth-register-label">
              Contraseña
            </label>
            <div className="auth-register-password-wrapper">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                required
                autoComplete="new-password"
                minLength={8}
                value={password}
                onChange={(e) => onPasswordChange(e.target.value)}
                onKeyUp={handlePasswordKeyEvent}
                onKeyDown={handlePasswordKeyEvent}
                className="layout-auth-input auth-register-password-input"
                placeholder="Mínimo 8 caracteres"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="auth-register-password-toggle"
                tabIndex={-1}
                aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {capsLock && (
              <p className="auth-register-capslock">
                <AlertTriangle size={14} />
                Caps Lock activado
              </p>
            )}
          </div>

          {error && (
            <p className="auth-register-error" role="alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="layout-auth-submit"
          >
            {submitting && <Loader2 className="auth-register-icon-spin" />}
            {submitting ? 'Registrando...' : 'Crear cuenta'}
          </button>
        </form>

        <p className="auth-register-footer">
          Ya tienes cuenta?{' '}
          <Link href="/login" className="auth-register-link">
            Inicia sesión
          </Link>
        </p>
      </div>
    </div>
  );
}
