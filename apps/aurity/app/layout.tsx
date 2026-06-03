// =============================================================================
// AURITY FRAMEWORK - Root Layout
// =============================================================================
// Next.js 14 root layout component
// Sprint: SPR-2025W44
// Version: 0.1.0
// Updated: Self-hosted JWT Authentication + Always-Visible User Display
// =============================================================================

import type { Metadata } from 'next';
import { Suspense } from 'react';
import './globals.css';
import 'fi-glass/theme.css';
import '@/polyfills';
import { GlobalPolicyBanner } from '@/components/policy/GlobalPolicyBanner';
import { ThemeProvider } from '@/components/shared/ThemeProvider';
import { AuthProvider } from '@/components/auth/AuthProvider';
import { ProtectedLayout } from '@/components/auth/ProtectedLayout';
import { ConditionalChatWidget } from '@/components/chat/ConditionalChatWidget';
import { MockBootstrap } from '@/components/dev/MockBootstrap';
import { AudioPlayerProvider } from '@/components/chat/AudioPlayerContext';
import { AudioConsentBanner } from '@/components/audio/AudioConsentBanner';
import { VersionBadge } from '@/components/dev/VersionBadge';
import { DesktopSetupWizard } from '@/components/onboarding/DesktopSetupWizard';
import { DesktopReadySignal } from '@/components/desktop/DesktopReadySignal';
import { EnvironmentProvider } from '@/lib/environment';

export const metadata: Metadata = {
  title: 'Free Intelligence · AURITY',
  description: 'Asistente médico con IA en la nube. Tus datos seguros, notas SOAP automáticas, asesoría clínica basada en evidencia. Opción self-hosted disponible.',
  keywords: ['healthcare', 'cloud AI', 'data security', 'PHI', 'HIPAA', 'medical AI', 'SOAP notes', 'clinical advisor', 'telemedicine', 'self-hosted'],

  // Open Graph (WhatsApp, Facebook, LinkedIn)
  openGraph: {
    title: 'Free Intelligence · AURITY',
    description: 'Asistente médico con IA en la nube. Tus datos siempre seguros, con opción de instalación propia.',
    url: 'https://app.aurity.io/chat',
    siteName: 'Free Intelligence',
    images: [
      {
        url: 'https://app.aurity.io/og-banner.png',
        width: 1200,
        height: 630,
        alt: 'Free Intelligence - IA Médica Segura en la Nube',
      },
    ],
    locale: 'es_MX',
    type: 'website',
  },

  // Twitter Card
  twitter: {
    card: 'summary_large_image',
    title: 'Free Intelligence · AURITY',
    description: 'Asistente médico con IA en la nube. Tus datos siempre seguros, con opción de instalación propia.',
    images: ['https://app.aurity.io/og-banner.png'],
    creator: '@freeintelligence',
  },

  // Additional metadata
  authors: [{ name: 'Dr. Bernard Uriza Orozco' }],
  creator: 'Free Intelligence Team',
  robots: {
    index: true,
    follow: true,
  },
  icons: {
    icon: '/favicon.png',
    shortcut: '/favicon.png',
    apple: '/favicon.png',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="min-h-screen bg-slate-900 antialiased">
        <MockBootstrap />
        <DesktopReadySignal />
        <EnvironmentProvider>
          <AuthProvider>
            <ThemeProvider>
              <AudioPlayerProvider>
                {/* DesktopSetupWizard must be OUTSIDE ProtectedLayout to show without auth */}
                <DesktopSetupWizard />
                <ProtectedLayout>
                  <GlobalPolicyBanner />
                  {children}
                  {/* Suspense required for useSearchParams in ConditionalChatWidget */}
                  <Suspense fallback={null}>
                    <ConditionalChatWidget />
                  </Suspense>
                  <AudioConsentBanner />
                  <VersionBadge />
                </ProtectedLayout>
              </AudioPlayerProvider>
            </ThemeProvider>
          </AuthProvider>
        </EnvironmentProvider>
      </body>
    </html>
  );
}
