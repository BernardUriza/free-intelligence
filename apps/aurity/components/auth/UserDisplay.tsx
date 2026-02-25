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
  } = useAuth();

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
  }, [dropdownOpen]);

  // Extract role from user context
  useEffect(() => {
    if (isAuthenticated && user?.roles?.length) {
      setUserRole(user.roles[0] || 'USER');
    }
  }, [isAuthenticated, user]);

  // Loading state
  if (isLoading) {
    return (
      <div className="usr-loading-container">
        <div className="usr-loading-avatar" />
        <div className="usr-loading-info">
          <div className="usr-loading-name" />
          <div className="usr-loading-role" />
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
        return 'usr-role-medico fi-text-green';
      case 'ENFERMERA':
        return 'usr-role-enfermera fi-text-primary';
      case 'ADMIN':
        return 'usr-role-admin fi-text-purple';
      default:
        return 'usr-role-default';
    }
  };

  // Render dropdown in portal
  const dropdownContent = dropdownOpen && mounted ? createPortal(
    <>
      {/* Backdrop to close dropdown */}
      <div
        className="usr-dropdown-backdrop"
        onClick={() => setDropdownOpen(false)}
      />

      {/* Dropdown Content - Portal ensures it's not clipped */}
      <div
        className="usr-dropdown-panel"
        style={{
          top: `${dropdownPosition.top}px`,
          right: `${dropdownPosition.right}px`,
        }}
      >
        {/* User Info Header */}
        <div className="usr-dropdown-header fi-border-bottom">
          <p className="fi-text-xs usr-dropdown-header-label">Usuario Actual</p>
          <p className="fi-title-sm-medium usr-dropdown-header-email">{user?.email}</p>
          {user?.email_verified && (
            <div className="usr-verified-badge">
              <CheckCircle2 className="usr-verified-icon" />
              <span className="usr-verified-text fi-text-green">Email verificado</span>
            </div>
          )}
        </div>

        {/* Menu Items */}
        <div className="usr-menu-section">
          <button
            onClick={() => {
              setDropdownOpen(false);
              router.push('/profile');
            }}
            className="usr-menu-item fi-text"
          >
            <User className="usr-menu-icon" />
            Mi Perfil
          </button>

          {/* Configuración - SUPERADMIN ONLY */}
          {isSuperAdmin && (
            <button
              onClick={() => {
                setDropdownOpen(false);
                router.push('/config');
              }}
              className="usr-menu-item fi-text"
            >
              <Settings className="usr-menu-icon" />
              Configuración
              <Star className="usr-menu-star fi-text-purple" />
            </button>
          )}

          {/* Desktop Setup Wizard - Desktop Mode Only */}
          {isDesktop() && (
            <button
              onClick={() => {
                setDropdownOpen(false);
                resetDesktopSetupWizard();
              }}
              className="usr-menu-item fi-text"
            >
              <Wrench className="usr-menu-icon" />
              Asistente de Instalación
            </button>
          )}
        </div>

        {/* Logout Button */}
        <div className="fi-border-top usr-menu-divider">
          <button
            onClick={async () => {
              setDropdownOpen(false);
              try {
                await logout({ logoutParams: { returnTo: window.location.origin + '/chat' } });
              } catch {
                // Logout failed silently — user stays on current page
              }
            }}
            className="usr-menu-item-danger fi-text-error"
          >
            <LogOut className="usr-menu-icon" />
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
        className="usr-trigger"
      >
        {/* Compact Avatar */}
        <div className="usr-avatar-wrapper">
          {user?.picture ? (
            <img
              src={user.picture}
              alt={user.name || 'User'}
              className="usr-avatar-img"
            />
          ) : (
            <div className="usr-avatar-fallback">
              {user?.name?.charAt(0).toUpperCase() || 'U'}
            </div>
          )}
          {/* Minimal online indicator */}
          <div className="usr-online-indicator" />
        </div>

        {/* Compact User Info */}
        <div className="usr-info-row">
          <span className="fi-text-xs-medium usr-name">
            {user?.name?.split(' ')[0] || user?.email?.split('@')[0] || 'User'}
          </span>
          <span className={`usr-role-badge ${getRoleBadgeColor(userRole)}`}>
            {userRole === 'MEDICO' ? 'MD' : userRole === 'ENFERMERA' ? 'RN' : userRole === 'ADMIN' ? 'ADM' : 'USR'}
          </span>
        </div>

        {/* Minimal Dropdown Arrow */}
        <ChevronDown
          className={dropdownOpen ? 'usr-chevron-open' : 'usr-chevron'}
        />
      </button>

      {/* Dropdown rendered in portal */}
      {dropdownContent}
    </>
  );
}
