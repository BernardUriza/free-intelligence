/**
 * CheckinQRDisplay - QR Code Display for TV
 *
 * Card: FI-CHECKIN-001
 * Shows scannable QR code on waiting room TV for patient check-in
 */

'use client';

import { useEffect, useState, useCallback } from 'react';
import { QrCode, RefreshCw, Smartphone } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface CheckinQRDisplayProps {
  clinicId: string;
  clinicName?: string;
  /** Refresh interval in seconds (default: 4 minutes) */
  refreshInterval?: number;
  /** Compact mode for sidebar display */
  compact?: boolean;
}

interface QRData {
  qrDataUrl: string;
  expiresAt: Date;
}

/**
 * Generate QR code locally using canvas
 * In production, this would call the backend API
 */
async function generateQRCode(clinicId: string): Promise<QRData> {
  // For MVP: Generate URL that will be encoded in QR
  const baseUrl = typeof window !== 'undefined'
    ? window.location.origin
    : 'https://app.aurity.io';

  const timestamp = Date.now();
  const nonce = Math.random().toString(36).substring(2, 10);
  const expiresAt = new Date(timestamp + 5 * 60 * 1000); // 5 minutes

  const checkinUrl = `${baseUrl}/checkin?clinic=${clinicId}&t=${timestamp}&n=${nonce}`;

  // Use dynamic import for QR code generation
  // This keeps bundle size small and loads only when needed
  try {
    const QRCode = (await import('qrcode')).default;
    const qrDataUrl = await QRCode.toDataURL(checkinUrl, {
      width: 256,
      margin: 2,
      color: {
        dark: '#1e1b4b', // Indigo-950
        light: '#ffffff',
      },
      errorCorrectionLevel: 'M',
    });

    return { qrDataUrl, expiresAt };
  } catch (error) {
    console.error('QR generation failed:', error);
    // Return placeholder if QRCode library not available
    return {
      qrDataUrl: '',
      expiresAt,
    };
  }
}

export function CheckinQRDisplay({
  clinicId,
  clinicName = 'Clínica',
  refreshInterval = 240, // 4 minutes
  compact = false,
}: CheckinQRDisplayProps) {
  const [qrData, setQrData] = useState<QRData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeLeft, setTimeLeft] = useState<number>(0);

  const refreshQR = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await generateQRCode(clinicId);
      setQrData(data);
      setTimeLeft(Math.floor((data.expiresAt.getTime() - Date.now()) / 1000));
    } catch (err) {
      setError('Error generando código QR');
      console.error('QR generation error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [clinicId]);

  // Initial load and refresh interval
  useEffect(() => {
    refreshQR();

    const interval = setInterval(refreshQR, refreshInterval * 1000);
    return () => clearInterval(interval);
  }, [refreshQR, refreshInterval]);

  // Countdown timer
  useEffect(() => {
    if (timeLeft <= 0) return;

    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          refreshQR();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft, refreshQR]);

  // Format time remaining
  const formatTimeLeft = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (compact) {
    return (
      <div className="bg-gradient-to-br from-indigo-950/40 to-purple-950/40 border border-indigo-600/40 rounded-xl p-4 backdrop-blur-sm">
        <div className="fi-flex-gap-lg">
          {/* QR Code */}
          <div className="flex-shrink-0">
            {isLoading ? (
              <div className="w-20 h-20 bg-slate-800 rounded-lg flex items-center justify-center">
                <RefreshCw className="w-6 h-6 text-indigo-400 animate-spin" />
              </div>
            ) : qrData?.qrDataUrl ? (
              <img
                src={qrData.qrDataUrl}
                alt="Check-in QR Code"
                className="w-20 h-20 rounded-lg"
              />
            ) : (
              <div className="w-20 h-20 bg-slate-800 rounded-lg flex items-center justify-center">
                <QrCode className="w-8 h-8 text-slate-600" />
              </div>
            )}
          </div>

          {/* Instructions */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-indigo-300">Check-in Rápido</p>
            <p className="fi-text-xs mt-1">
              Escanea con tu celular
            </p>
          </div>
        </div>
      </div>
    );
  }

  // FI-TV-007: TV Mode with 16:9 aspect ratio optimization
  // Full-height layout that fills the side panel properly
  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-indigo-950/40 to-purple-950/40 border border-indigo-600/30 rounded-xl backdrop-blur-sm p-3 sm:p-4 lg:p-6">
      {/* Header - Compact for TV */}
      <div className="text-center mb-3 sm:mb-4 flex-shrink-0">
        <div
          className="inline-flex items-center gap-2 px-3 py-1.5 bg-indigo-900/30 border border-indigo-500/30 rounded-full mb-2 sm:mb-3"
        >
          <Smartphone
            className="text-indigo-400"
            style={{ width: 'clamp(0.75rem, 1.5vw, 1.25rem)', height: 'clamp(0.75rem, 1.5vw, 1.25rem)' }}
          />
          <span
            className="font-medium text-indigo-300"
            style={{ fontSize: 'clamp(0.625rem, 1vw, 0.875rem)' }}
          >
            Check-in Digital
          </span>
        </div>
        <h3
          className="font-bold text-white mb-1"
          style={{ fontSize: 'clamp(1rem, 2vw, 1.75rem)' }}
        >
          ¿Tienes cita hoy?
        </h3>
        <p
          className="text-slate-400"
          style={{ fontSize: 'clamp(0.625rem, 1vw, 0.875rem)' }}
        >
          Escanea el código QR
        </p>
      </div>

      {/* QR Code - Flexible size that fills available space */}
      <div className="flex-1 flex items-center justify-center min-h-0 mb-3 sm:mb-4">
        <div className="relative w-full max-w-[90%] aspect-square flex items-center justify-center">
          {isLoading ? (
            <div className="w-full h-full max-w-[200px] max-h-[200px] bg-slate-800/50 rounded-2xl flex items-center justify-center">
              <RefreshCw
                className="text-indigo-400 animate-spin"
                style={{ width: 'clamp(2rem, 5vw, 4rem)', height: 'clamp(2rem, 5vw, 4rem)' }}
              />
            </div>
          ) : error ? (
            <div className="w-full h-full max-w-[200px] max-h-[200px] bg-slate-800/50 rounded-2xl flex flex-col items-center justify-center p-4">
              <QrCode
                className="text-slate-600 mb-2"
                style={{ width: 'clamp(2rem, 5vw, 4rem)', height: 'clamp(2rem, 5vw, 4rem)' }}
              />
              <p
                className="fi-text-error text-center"
                style={{ fontSize: 'clamp(0.625rem, 1vw, 0.875rem)' }}
              >
                {error}
              </p>
              <Button
                onClick={refreshQR}
                variant="indigo"
                size="sm"
                className="mt-2"
                style={{ fontSize: 'clamp(0.625rem, 1vw, 0.75rem)' }}
              >
                Reintentar
              </Button>
            </div>
          ) : qrData?.qrDataUrl ? (
            <div
              className="bg-white rounded-xl sm:rounded-2xl shadow-2xl shadow-indigo-500/20 p-2 sm:p-3 lg:p-4"
              style={{ maxWidth: 'min(100%, 250px)', maxHeight: 'min(100%, 250px)' }}
            >
              <img
                src={qrData.qrDataUrl}
                alt="Check-in QR Code"
                className="w-full h-full object-contain"
                style={{
                  width: 'clamp(80px, 15vw, 200px)',
                  height: 'clamp(80px, 15vw, 200px)',
                }}
              />
            </div>
          ) : (
            <div className="w-full h-full max-w-[200px] max-h-[200px] bg-slate-800/50 rounded-2xl flex items-center justify-center">
              <QrCode
                className="text-slate-600"
                style={{ width: 'clamp(2rem, 5vw, 4rem)', height: 'clamp(2rem, 5vw, 4rem)' }}
              />
            </div>
          )}

          {/* Timer badge */}
          {!isLoading && !error && timeLeft > 0 && (
            <div
              className="absolute -bottom-2 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-slate-900 border border-slate-700 rounded-full"
            >
              <span
                className="text-slate-400"
                style={{ fontSize: 'clamp(0.5rem, 0.8vw, 0.75rem)' }}
              >
                Actualiza en {formatTimeLeft(timeLeft)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Instructions - Simplified for TV side panel */}
      <div className="flex-shrink-0 space-y-1.5 sm:space-y-2 hidden lg:block">
        {[
          { num: 1, text: 'Abre la cámara' },
          { num: 2, text: 'Apunta al código' },
          { num: 3, text: 'Confirma tu cita' },
        ].map(step => (
          <div
            key={step.num}
            className="flex items-center gap-2 p-2 bg-slate-900/50 rounded-lg"
          >
            <div
              className="rounded-full bg-indigo-600/20 flex items-center justify-center flex-shrink-0"
              style={{
                width: 'clamp(1.25rem, 2vw, 1.75rem)',
                height: 'clamp(1.25rem, 2vw, 1.75rem)',
              }}
            >
              <span
                className="font-bold text-indigo-400"
                style={{ fontSize: 'clamp(0.5rem, 0.8vw, 0.75rem)' }}
              >
                {step.num}
              </span>
            </div>
            <p
              className="text-white font-medium"
              style={{ fontSize: 'clamp(0.625rem, 1vw, 0.875rem)' }}
            >
              {step.text}
            </p>
          </div>
        ))}
      </div>

      {/* Footer - Minimal for TV */}
      <div className="flex-shrink-0 mt-3 sm:mt-4 pt-3 border-t border-indigo-700/30">
        <div className="flex items-center justify-center gap-2">
          <div
            className="bg-green-500 rounded-full animate-pulse"
            style={{ width: 'clamp(0.375rem, 0.6vw, 0.5rem)', height: 'clamp(0.375rem, 0.6vw, 0.5rem)' }}
          />
          <span
            className="text-slate-500"
            style={{ fontSize: 'clamp(0.5rem, 0.8vw, 0.75rem)' }}
          >
            {clinicName} · Sistema activo
          </span>
        </div>
      </div>
    </div>
  );
}
