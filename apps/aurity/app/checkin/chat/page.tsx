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
import { AlertCircle, QrCode, ArrowLeft } from 'lucide-react';
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
      <div className="fi-page-centered p-4">
        <div className="max-w-md w-full bg-slate-900/50 border border-slate-800 rounded-2xl p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-red-950/30 flex items-center justify-center">
            <AlertCircle className="fi-icon-xl fi-text-error" />
          </div>
          <h1 className="fi-title-2xl mb-2">
            Enlace inválido
          </h1>
          <p className="text-slate-400 mb-6">
            Este enlace de check-in no es válido o ha expirado.
            Por favor, escanea el código QR en la sala de espera.
          </p>
          <div className="flex items-center justify-center gap-2 text-sm text-slate-500">
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
          <div className="max-w-md w-full bg-slate-900/50 border border-slate-800 rounded-2xl p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-orange-950/30 flex items-center justify-center">
              <AlertCircle className="w-8 h-8 text-orange-400" />
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
              className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
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
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex flex-col">
      {/* Header with fallback link */}
      <header className="flex items-center justify-between px-4 py-3 bg-slate-900/80 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">A</span>
          </div>
          <div>
            <h1 className="text-white font-semibold">FI Receptionist</h1>
            <p className="fi-text-xs">Check-in conversacional</p>
          </div>
        </div>

        {/* Fallback to form-based check-in */}
        <Link
          href={`/checkin?${fallbackParams.toString()}`}
          className="flex items-center gap-2 px-3 py-1.5 fi-subtitle hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="hidden sm:inline">Formulario tradicional</span>
          <span className="sm:hidden">Formulario</span>
        </Link>
      </header>

      {/* Chat Widget - Full screen */}
      <main className="flex-1 relative">
        <ReceptionistChatWidget
          clinicId={clinicId}
          patientName={patientName || undefined}
          onCheckinComplete={(result) => {
            console.log('[ChatCheckin] Check-in completed:', result);
            // Could show success overlay or redirect
          }}
        />
      </main>

      {/* Footer */}
      <footer className="px-4 py-2 bg-slate-900/80 border-t border-slate-800 text-center">
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
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-indigo-600/20 flex items-center justify-center animate-pulse">
              <span className="text-2xl">🏥</span>
            </div>
            <p className="text-slate-400 animate-pulse">Iniciando asistente de check-in...</p>
          </div>
        </div>
      }
    >
      <ChatCheckinContent />
    </Suspense>
  );
}
