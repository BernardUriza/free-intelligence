'use client';

/**
 * Registration form state, validation, and submission.
 */

import { useState, useCallback, type FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/auth/AuthProvider';

const MIN_PASSWORD_LENGTH = 8;

export function useRegisterForm() {
  const router = useRouter();
  const { register, isAuthenticated, isLoading: authLoading } = useAuth();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const shouldRedirect = isAuthenticated && !authLoading;

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      setError('');

      if (password.length < MIN_PASSWORD_LENGTH) {
        setError(`La contraseña debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres`);
        return;
      }

      setSubmitting(true);
      try {
        await register(email, password, name);
        router.push('/chat');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error al registrarse');
      } finally {
        setSubmitting(false);
      }
    },
    [email, password, name, register, router],
  );

  return {
    name,
    setName,
    email,
    setEmail,
    password,
    setPassword,
    error,
    submitting,
    shouldRedirect,
    handleSubmit,
  };
}
