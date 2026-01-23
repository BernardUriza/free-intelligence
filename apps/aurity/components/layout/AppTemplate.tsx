/**
 * AppTemplate - Unified Layout Template
 * 
 * Centralizes PageHeader rendering in one place.
 * All pages use this template instead of calling PageHeader directly.
 */

import React, { ReactNode } from 'react';
import Image from 'next/image';
import { PageHeader, PageHeaderConfig } from './PageHeader';

interface AppTemplateProps {
  /** Page header configuration (optional - omit to hide header) */
  headerConfig?: PageHeaderConfig;
  /** Additional header actions (right side, before user) */
  headerActions?: ReactNode;
  /** Main content */
  children: ReactNode;
  /** Optional gradient background (default: slate) */
  backgroundGradient?: 'slate' | 'emerald' | 'purple' | 'none';
  /** Optional max-width container (default: 7xl) */
  maxWidth?: 'full' | '7xl' | '5xl' | '3xl';
  /** Optional padding (default: 6) */
  padding?: '0' | '4' | '6' | '8';
  /** Show logo watermark background (default: false) */
  showWatermark?: boolean;
  /** Show geometric background blobs (default: false) */
  showGeometricBg?: boolean;
  /** Use full viewport height with flex layout (default: false) */
  fullHeight?: boolean;
}

export function AppTemplate({
  headerConfig,
  headerActions,
  children,
  backgroundGradient = 'slate',
  maxWidth = '7xl',
  padding = '6',
  showWatermark = false,
  showGeometricBg = false,
  fullHeight = false,
}: AppTemplateProps) {
  const backgroundClasses = {
    slate: 'bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950',
    emerald: 'bg-gradient-to-br from-emerald-950 via-slate-900 to-slate-950',
    purple: 'bg-gradient-to-br from-purple-950 via-slate-900 to-slate-950',
    none: 'bg-slate-950',
  };

  const maxWidthClasses = {
    full: 'w-full',
    '7xl': 'max-w-7xl',
    '5xl': 'max-w-5xl',
    '3xl': 'max-w-3xl',
  };

  const paddingClasses = {
    '0': 'p-0',
    '4': 'p-4',
    '6': 'p-6',
    '8': 'p-8',
  };

  // Container classes based on fullHeight mode
  // Note: overflow-hidden only for fullHeight mode (chat, etc.)
  // Normal pages need overflow-y-auto to scroll
  const containerClasses = fullHeight
    ? `h-screen h-[100dvh] flex flex-col ${backgroundClasses[backgroundGradient]} relative overflow-hidden`
    : `min-h-screen ${backgroundClasses[backgroundGradient]} relative overflow-y-auto`;

  // Main content classes based on fullHeight mode
  const mainClasses = fullHeight
    ? `flex-1 ${maxWidthClasses[maxWidth]} mx-auto ${paddingClasses[padding]} relative z-10 overflow-hidden flex flex-col`
    : `${maxWidthClasses[maxWidth]} mx-auto ${paddingClasses[padding]} relative z-10`;

  return (
    <div className={containerClasses}>
      {/* Abstract geometric background */}
      {showGeometricBg && (
        <div className="fixed inset-0 opacity-[0.02] pointer-events-none">
          <div className="absolute top-1/4 left-1/3 w-[600px] h-[600px] bg-emerald-400 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/3 w-[600px] h-[600px] bg-cyan-400 rounded-full blur-3xl" />
        </div>
      )}

      {/* Aurity Logo Watermark */}
      {showWatermark && (
        <div className="fixed inset-0 flex items-center justify-center opacity-[0.03] pointer-events-none">
          <Image
            src="/logos/aurity-logo-light.png"
            alt=""
            width={800}
            height={200}
            className="w-auto h-auto max-w-[60%]"
            priority={false}
          />
        </div>
      )}

      {/* Unified PageHeader - rendered once here (optional) */}
      {headerConfig && <PageHeader {...headerConfig} actions={headerActions} />}

      {/* Main Content */}
      <main className={mainClasses}>
        {children}
      </main>
    </div>
  );
}
