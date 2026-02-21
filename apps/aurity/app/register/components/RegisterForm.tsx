'use client';

/**
 * Registration form UI — name, email, password fields with validation feedback.
 */

import { type FormEvent } from 'react';
import { Loader2 } from 'lucide-react';
import Link from 'next/link';

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
  return (
    <div className="auth-register-wrapper">
      <div className="auth-register-card">
        <h1 className="auth-register-title">AURITY</h1>
        <p className="auth-register-subtitle">Crea tu cuenta</p>

        <form onSubmit={onSubmit} className="auth-register-form" noValidate>
          <FormField
            id="name"
            label="Nombre"
            type="text"
            autoComplete="name"
            placeholder="Dr. Juan Perez"
            value={name}
            onChange={onNameChange}
          />

          <FormField
            id="email"
            label="Email"
            type="email"
            autoComplete="email"
            placeholder="tu@correo.com"
            value={email}
            onChange={onEmailChange}
          />

          <FormField
            id="password"
            label="Contraseña"
            type="password"
            autoComplete="new-password"
            placeholder="Mínimo 8 caracteres"
            minLength={8}
            value={password}
            onChange={onPasswordChange}
          />

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

/** Reusable labeled input field. */
function FormField({
  id,
  label,
  type,
  autoComplete,
  placeholder,
  value,
  minLength,
  onChange,
}: {
  id: string;
  label: string;
  type: string;
  autoComplete: string;
  placeholder: string;
  value: string;
  minLength?: number;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="auth-register-label">
        {label}
      </label>
      <input
        id={id}
        type={type}
        required
        autoComplete={autoComplete}
        minLength={minLength}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="layout-auth-input"
        placeholder={placeholder}
      />
    </div>
  );
}
