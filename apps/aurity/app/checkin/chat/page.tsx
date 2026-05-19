/**
 * FI Receptionist Chat Page
 *
 * Card: FI-CHECKIN-005
 * Conversational check-in using ChatWidget with receptionist configuration
 *
 * URL: /checkin/chat?clinic=xxx&t=xxx&n=xxx
 *
 * This provides a conversational alternative to the form-based CheckinFlow
 * for patients who prefer natural language interaction.
 */

'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { AlertCircle, QrCode, ArrowLeft, Building2 } from 'lucide-react';
import Link from 'next/link';
import { ReceptionistChatWidget } from '@/components/checkin/ReceptionistChatWidget';

function ChatCheckinContent() {
  const searchParams = useSearchParams();
  // router available via useRouter() if needed for navigation

  const clinicId = searchParams.get('clinic');
  const timestamp = searchParams.get('t');
  const nonce = searchParams.get('n');
  const patientName = searchParams.get('name'); // Optional: pre-fill patient name

  // Validate QR parameters
  if (!clinicId) {
    return (
      <div className="chk-page-centered">
        <div className="checkin-card">
          <div className="checkin-icon-wrapper checkin-icon-error">
            <AlertCircle className="fi-icon-xl fi-text-error" />
          </div>
          <h1 className="chk-title">
            Enlace inválido
          </h1>
          <p className="chk-body-muted">
            Este enlace de check-in no es válido o ha expirado.
            Por favor, escanea el código QR en la sala de espera.
          </p>
          <div className="checkin-hint">
            <QrCode className="fi-icon-sm" />
            <span>Escanea el QR para hacer check-in</span>
          </div>
        </div>
      </div>
    );
  }

  // Check if QR is expired (5 minutes validity)
  if (timestamp) {
    const qrTime = parseInt(timestamp, 10);
    const now = Date.now();
    const fiveMinutes = 5 * 60 * 1000;

    if (now - qrTime > fiveMinutes) {
      return (
        <div className="chk-page-centered">
          <div className="checkin-card">
            <div className="checkin-icon-wrapper checkin-icon-warning">
              <AlertCircle className="chk-alert-icon" />
            </div>
            <h1 className="chk-title">
              Código QR expirado
            </h1>
            <p className="chk-body-muted">
              Este código QR ha expirado por seguridad.
              Por favor, escanea el código QR actualizado en la pantalla de la sala de espera.
            </p>
            <button
              onClick={() => window.close()}
              className="chk-btn-close"
            >
              Cerrar
            </button>
          </div>
        </div>
      );
    }
  }

  // Build URL params to pass to fallback link
  const fallbackParams = new URLSearchParams();
  fallbackParams.set('clinic', clinicId);
  if (timestamp) fallbackParams.set('t', timestamp);
  if (nonce) fallbackParams.set('n', nonce);

  return (
    <div className="chk-page-layout">
      {/* Header with fallback link */}
      <header className="chk-header">
        <div className="chk-header-brand">
          <div className="chk-header-logo">
            <span className="chk-header-logo-text">A</span>
          </div>
          <div>
            <h1 className="chk-header-title">FI Receptionist</h1>
            <p className="fi-text-xs">Check-in conversacional</p>
          </div>
        </div>

        {/* Fallback to form-based check-in */}
        <Link
          href={`/checkin?${fallbackParams.toString()}`}
          className="chk-fallback-link"
        >
          <ArrowLeft className="chk-fallback-icon" />
          <span className="chk-fallback-label-full">Formulario tradicional</span>
          <span className="chk-fallback-label-short">Formulario</span>
        </Link>
      </header>

      {/* Chat Widget - Full screen */}
      <main className="chk-main">
        <ReceptionistChatWidget
          clinicId={clinicId}
          patientName={patientName || undefined}
          onCheckinComplete={() => {
            // Check-in completed — success handled by ReceptionistChatWidget UI
          }}
        />
      </main>

      {/* Footer */}
      <footer className="chk-footer">
        <p className="fi-text-xs-muted">
          100% Local · Datos protegidos · Powered by AURITY
        </p>
      </footer>
    </div>
  );
}

export default function ChatCheckinPage() {
  return (
    <Suspense
      fallback={
        <div className="chk-loading-wrapper">
          <div className="chk-loading-content">
            <div className="chk-loading-icon-ring">
              <Building2 className="chk-loading-icon" strokeWidth={1.5} aria-hidden="true" />
            </div>
            <p className="chk-loading-text">Iniciando asistente de check-in...</p>
          </div>
        </div>
      }
    >
      <ChatCheckinContent />
    </Suspense>
  );
}
