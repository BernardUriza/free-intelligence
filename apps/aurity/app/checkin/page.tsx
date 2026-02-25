/**
 * Check-in Page
 *
 * Card: FI-CHECKIN-001
 * Patient self-service check-in page (accessed via QR code)
 *
 * URL: /checkin?clinic=xxx&t=xxx&n=xxx
 */

'use client';

import { Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { CheckinFlow } from '@/components/checkin';
import { AlertCircle, QrCode, MessageCircle } from 'lucide-react';

function CheckinContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const clinicId = searchParams.get('clinic');
  const timestamp = searchParams.get('t');
  const nonce = searchParams.get('n');

  // Validate QR parameters
  if (!clinicId) {
    return (
      <div className="fi-page-centered p-4">
        <div className="checkin-card">
          <div className="checkin-icon-wrapper checkin-icon-error">
            <AlertCircle className="fi-icon-xl fi-text-error" />
          </div>
          <h1 className="fi-title-2xl mb-2">
            Enlace inválido
          </h1>
          <p className="text-slate-400 mb-6">
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
        <div className="fi-page-centered p-4">
          <div className="checkin-card">
            <div className="checkin-icon-wrapper checkin-icon-warning">
              <AlertCircle className="fi-icon-xl text-orange-400" />
            </div>
            <h1 className="fi-title-2xl mb-2">
              Código QR expirado
            </h1>
            <p className="text-slate-400 mb-6">
              Este código QR ha expirado por seguridad.
              Por favor, escanea el código QR actualizado en la pantalla de la sala de espera.
            </p>
            <button
              onClick={() => window.close()}
              className="checkin-btn-close"
            >
              Cerrar
            </button>
          </div>
        </div>
      );
    }
  }

  const clinicName = 'Clínica AURITY';

  // Build params for chat mode link
  const chatParams = new URLSearchParams();
  chatParams.set('clinic', clinicId);
  if (timestamp) chatParams.set('t', timestamp);
  if (nonce) chatParams.set('n', nonce);

  return (
    <div className="relative">
      {/* Floating Chat Mode Toggle */}
      <Link
        href={`/checkin/chat?${chatParams.toString()}`}
        className="checkin-fab-chat"
      >
        <MessageCircle className="w-5 h-5" />
        <span className="hidden sm:inline">Prefiero chatear</span>
      </Link>

      <CheckinFlow
      clinicId={clinicId}
      clinicName={clinicName}
      onComplete={(response) => {
        console.log('Check-in completed:', response);
      }}
      onCancel={() => {
        // Close tab or go back
        if (window.opener) {
          window.close();
        } else {
          router.push('/');
        }
      }}
    />
    </div>
  );
}

export default function CheckinPage() {
  return (
    <Suspense
      fallback={
        <div className="checkin-loading-page">
          <div className="animate-pulse text-slate-400">Cargando check-in...</div>
        </div>
      }
    >
      <CheckinContent />
    </Suspense>
  );
}
