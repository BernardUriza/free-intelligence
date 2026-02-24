'use client';

/**
 * Register Page — composition root.
 * Delegates form state to useRegisterForm and rendering to RegisterForm.
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useRegisterForm } from './hooks/useRegisterForm';
import { RegisterForm } from './components/RegisterForm';

export default function RegisterPage() {
  const router = useRouter();
  const {
    name, setName,
    email, setEmail,
    password, setPassword,
    error,
    submitting,
    shouldRedirect,
    handleSubmit,
  } = useRegisterForm();

  useEffect(() => {
    if (shouldRedirect) {
      router.replace('/chat');
    }
  }, [shouldRedirect, router]);

  if (shouldRedirect) return null;

  return (
    <RegisterForm
      name={name}
      email={email}
      password={password}
      error={error}
      submitting={submitting}
      onNameChange={setName}
      onEmailChange={setEmail}
      onPasswordChange={setPassword}
      onSubmit={handleSubmit}
    />
  );
}
