/**
 * AppNavigation Component - Global Navigation Menu
 *
 * Dropdown menu accessible from any page via PageHeader.
 * Shows all routes from NAV_ROUTES grouped by category.
 *
 * Card: FI-UI-FEAT-NAV-001
 * Updated: 2025-12-12 - Use centralized getGroupedRoutes()
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu, X, Home, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getGroupedRoutes } from '@/lib/navigation';

// Check if running in desktop mode (Tauri)
const checkIsDesktop = () => {
  if (typeof window === 'undefined') return false;
  if ('__TAURI__' in window) return true;
  if (process.env.NEXT_PUBLIC_DEPLOYMENT_TARGET === 'desktop') return true;
  return false;
};

interface AppNavigationProps {
  /** Compact mode for header integration */
  compact?: boolean;
}

export function AppNavigation({ compact = false }: AppNavigationProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);
  const pathname = usePathname();
  const menuRef = useRef<HTMLDivElement>(null);

  // Check for desktop mode on mount
  useEffect(() => {
    setIsDesktop(checkIsDesktop());
  }, []);

  // Close on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }

    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen]);

  // Close on route change
  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

  const isCurrentRoute = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };

  return (
    <div className="relative" ref={menuRef}>
      {/* Trigger Button */}
      <Button
        onClick={() => setIsOpen(!isOpen)}
        className={isOpen ? 'fi-nav-trigger-open' : 'fi-nav-trigger-closed'}
        aria-label="Navigation menu"
        aria-expanded={isOpen}
        variant="ghost"
        size="sm"
      >
        {isOpen ? (
          <X className="fi-icon-md" />
        ) : (
          <Menu className="fi-icon-md" />
        )}
        {!compact && <span className="text-sm font-medium">Menu</span>}
      </Button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="fi-dropdown-nav">
          {/* Home link */}
          <Link
            href="/"
            className={isCurrentRoute('/') ? 'fi-nav-link-home-active' : 'fi-nav-link-home'}
          >
            <Home className="fi-icon-md" />
            <span className="font-medium">Inicio</span>
            <ChevronRight className="fi-icon-sm ml-auto opacity-50" />
          </Link>

          <div className="h-px bg-slate-700 my-2" />

          {/* Grouped Routes (from centralized navigation config) */}
          {getGroupedRoutes().map(({ category, routes }) => {
            // Filter out webOnly routes when in desktop mode
            const filteredRoutes = isDesktop
              ? routes.filter(r => !r.webOnly)
              : routes;

            // Skip empty categories
            if (filteredRoutes.length === 0) return null;

            return (
              <div key={category.id} className="mb-2">
                {/* Category Label */}
                <div className="px-4 py-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                  <span>{category.icon}</span>
                  <span>{category.label}</span>
                </div>

                {/* Category Routes */}
                {filteredRoutes.map((route) => {
                  const Icon = route.icon;
                  const isCurrent = isCurrentRoute(route.href);

                  return (
                    <Link
                      key={route.id}
                      href={route.href}
                      className={isCurrent ? 'fi-nav-link-active' : 'fi-nav-link'}
                    >
                      <Icon className={`w-4 h-4 ${isCurrent ? 'fi-text-primary' : 'text-slate-500 group-hover:fi-text'}`} />
                      <span className="flex-1 text-sm">{route.title}</span>

                      {/* Badge */}
                      {route.badge && (
                        <span className={route.badge === 'Superadmin' ? 'fi-nav-badge-superadmin' : route.badge === 'Admin' ? 'fi-nav-badge-admin' : route.badge === 'AI' ? 'fi-nav-badge-ai' : 'fi-nav-badge-default'}>
                          {route.badge}
                        </span>
                      )}

                      {/* Keyboard Shortcut */}
                      <kbd className="fi-kbd">{route.shortcut}</kbd>
                    </Link>
                  );
                })}
              </div>
            );
          })}

          {/* Footer hint */}
          <div className="px-4 py-2 mt-2 fi-border-top">
            <p className="fi-text-xs-muted">
              Tip: Usa atajos 1-9 desde el inicio
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
