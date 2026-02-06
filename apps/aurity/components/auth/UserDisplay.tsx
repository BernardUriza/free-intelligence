'use client';

/**
 * UserDisplay Component
 * HIPAA Card: G-003 - Auth Integration
 *
 * Always-visible user authentication display.
 * Shows:
 * - User avatar + name + role (when logged in)
 * - Login button (when logged out)
 * - Logout dropdown
 */

import { useAuth } from '@/components/auth/AuthProvider';
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { createPortal } from 'react-dom';
import { LogIn, CheckCircle2, User, Settings, Star, LogOut, ChevronDown, Wrench } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useRBAC } from '@aurity-standalone/hooks/useRBAC';
import { isDesktop } from '@/lib/config/deployment';
import { resetDesktopSetupWizard } from '@/components/onboarding/DesktopSetupWizard';

export function UserDisplay() {
  const {
    user,
    isAuthenticated,
    isLoading,
    loginWithRedirect,
    logout,
    getAccessTokenSilently,
  } = useAuth();

  // Debug: Verify logout is defined
  useEffect(() => {
    console.log('[UserDisplay] logout function:', typeof logout, logout);
  }, [logout]);

  const { isSuperAdmin } = useRBAC();
  const router = useRouter();
  const [userRole, setUserRole] = useState<string>('');
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, right: 0 });

  // Mount portal
  useEffect(() => {
    setMounted(true);
  }, []);

  // Calculate dropdown position when opened
  useEffect(() => {
    if (dropdownOpen && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.bottom + 8, // 8px gap below button
        right: window.innerWidth - rect.right, // Distance from right edge
      });
    }
  }, [dropdownOpen]); // TODO: Add window dimensions tracking if needed for responsiveness

  // Extract role from user context
  useEffect(() => {
    if (isAuthenticated && user?.roles?.length) {
      setUserRole(user.roles[0] || 'USER');
    }
  }, [isAuthenticated, user]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 rounded-lg border border-slate-700">
        <div className="w-8 h-8 rounded-full bg-slate-700 animate-pulse" />
        <div className="flex flex-col gap-1">
          <div className="w-24 h-3 bg-slate-700 rounded animate-pulse" />
          <div className="w-16 h-2 bg-slate-700 rounded animate-pulse" />
        </div>
      </div>
    );
  }

  // Not authenticated - show login button
  if (!isAuthenticated) {
    return (
      <Button
        onClick={() => loginWithRedirect()}
        variant="primary"
        icon={LogIn}
      >
        Iniciar Sesión
      </Button>
    );
  }

  // Authenticated - show compact user display
  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'MEDICO':
        return 'bg-green-500/20 fi-text-green';
      case 'ENFERMERA':
        return 'bg-blue-500/20 fi-text-primary';
      case 'ADMIN':
        return 'bg-purple-500/20 fi-text-purple';
      default:
        return 'bg-gray-500/20 text-gray-400';
    }
  };

  // Render dropdown in portal
  const dropdownContent = dropdownOpen && mounted ? createPortal(
    <>
      {/* Backdrop to close dropdown */}
      <div
        className="fixed inset-0 z-[9998]"
        onClick={() => setDropdownOpen(false)}
      />

      {/* Dropdown Content - Portal ensures it's not clipped */}
      <div
        className="fixed w-64 bg-slate-800 rounded-lg shadow-2xl border border-slate-700 z-[10000] overflow-hidden"
        style={{
          top: `${dropdownPosition.top}px`,
          right: `${dropdownPosition.right}px`,
        }}
      >
        {/* User Info Header */}
        <div className="px-4 py-3 bg-slate-900/50 fi-border-bottom">
          <p className="fi-text-xs uppercase tracking-wider font-semibold mb-1">Usuario Actual</p>
          <p className="fi-title-sm-medium truncate">{user?.email}</p>
          {user?.email_verified && (
            <div className="flex items-center gap-1 mt-1">
              <CheckCircle2 className="w-3 h-3 text-green-500" />
              <span className="text-xs fi-text-green">Email verificado</span>
            </div>
          )}
        </div>

        {/* Menu Items */}
        <div className="py-2">
          <button
            onClick={() => {
              setDropdownOpen(false);
              router.push('/profile');
            }}
            className="w-full px-4 py-2 text-left text-sm fi-text hover:bg-slate-700 hover:text-white transition-colors flex items-center gap-2"
          >
            <User className="w-4 h-4" />
            Mi Perfil
          </button>

          {/* Configuración - SUPERADMIN ONLY */}
          {isSuperAdmin && (
            <button
              onClick={() => {
                setDropdownOpen(false);
                router.push('/config');
              }}
              className="w-full px-4 py-2 text-left text-sm fi-text hover:bg-slate-700 hover:text-white transition-colors flex items-center gap-2"
            >
              <Settings className="w-4 h-4" />
              Configuración
              <Star className="w-3 h-3 fi-text-purple ml-auto fill-purple-400" />
            </button>
          )}

          {/* Desktop Setup Wizard - Desktop Mode Only */}
          {isDesktop() && (
            <button
              onClick={() => {
                setDropdownOpen(false);
                resetDesktopSetupWizard();
              }}
              className="w-full px-4 py-2 text-left text-sm fi-text hover:bg-slate-700 hover:text-white transition-colors flex items-center gap-2"
            >
              <Wrench className="w-4 h-4" />
              Asistente de Instalación
            </button>
          )}
        </div>

        {/* Logout Button */}
        <div className="fi-border-top py-2">
          <button
            onClick={async () => {
              console.log('[UserDisplay] Logout button clicked');
              setDropdownOpen(false);
              try {
                console.log('[UserDisplay] Calling logout...');
                // Logout without redirecting back to origin to allow user to continue using the app unauthenticated
                await logout({ logoutParams: { returnTo: window.location.origin + '/chat' } });
                console.log('[UserDisplay] Logout completed');
              } catch (error) {
                console.error('[UserDisplay] Logout failed:', error);
              }
            }}
            className="w-full px-4 py-2 text-left text-sm fi-text-error hover:bg-red-900/20 hover:text-red-300 transition-colors flex items-center gap-2"
          >
            <LogOut className="w-4 h-4" />
            Cerrar Sesión
          </button>
        </div>
      </div>
    </>,
    document.body
  ) : null;

  return (
    <>
      {/* Compact User Display Button */}
      <button
        ref={buttonRef}
        onClick={() => setDropdownOpen(!dropdownOpen)}
        className="flex items-center gap-2 px-2.5 py-1.5 bg-slate-800/60 hover:bg-slate-700/60 rounded-lg border border-slate-700/50 hover:border-slate-600/50 transition-all"
      >
        {/* Compact Avatar */}
        <div className="relative">
          {user?.picture ? (
            <img
              src={user.picture}
              alt={user.name || 'User'}
              className="w-7 h-7 rounded-full ring-1 ring-slate-600/50"
            />
          ) : (
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-medium text-xs ring-1 ring-slate-600/50">
              {user?.name?.charAt(0).toUpperCase() || 'U'}
            </div>
          )}
          {/* Minimal online indicator */}
          <div className="absolute -bottom-0.5 -right-0.5 w-2 h-2 bg-green-500 rounded-full border border-slate-800" />
        </div>

        {/* Compact User Info */}
        <div className="flex items-center gap-1.5">
          <span className="fi-text-xs-medium text-white/90 truncate max-w-[100px]">
            {user?.name?.split(' ')[0] || user?.email?.split('@')[0] || 'User'}
          </span>
          <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${getRoleBadgeColor(userRole)}`}>
            {userRole === 'MEDICO' ? 'MD' : userRole === 'ENFERMERA' ? 'RN' : userRole === 'ADMIN' ? 'ADM' : 'USR'}
          </span>
        </div>

        {/* Minimal Dropdown Arrow */}
        <ChevronDown
          className={`w-3 h-3 text-slate-400 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Dropdown rendered in portal */}
      {dropdownContent}
    </>
  );
}
