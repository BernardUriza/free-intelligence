'use client';

/**
 * Home Page - Slim Index Hub
 * Card: FI-UI-FEAT-209
 *
 * Minimal navigation hub for Aurity Framework
 * (Replaced full IndexHub with slim version - 63% lighter)
 *
 * Behavior:
 * - Unauthenticated users: auto-redirect to /chat
 * - Authenticated staff users: show SlimIndexHub
 * - Random authenticated users (no roles): redirect to /chat
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { useRBAC } from '@aurity-standalone/hooks/useRBAC';
import { SlimIndexHub } from '@/components/medical/SlimIndexHub';

export default function Home() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { roles, isSuperAdmin, isLoading: rbacLoading } = useRBAC();
  const router = useRouter();

  const isLoading = authLoading || rbacLoading;

  // Check if user has any staff/admin roles
  const hasStaffAccess = isSuperAdmin || roles.includes('FI-clinician');

  useEffect(() => {
    // Wait for auth to finish loading
    if (isLoading) return;

    // Unauthenticated users: redirect to /chat
    if (!isAuthenticated) {
      router.push('/chat');
      return;
    }

    // Authenticated but no staff access: redirect to /chat
    if (!hasStaffAccess) {
      router.push('/chat');
    }
  }, [isAuthenticated, isLoading, hasStaffAccess, router]);

  // Show nothing while loading or redirecting
  if (isLoading || !isAuthenticated || !hasStaffAccess) {
    return null;
  }

  // Authenticated staff users see the SlimIndexHub
  return <SlimIndexHub />;
}
