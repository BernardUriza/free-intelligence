'use client';

/**
 * SuccessStep Component
 *
 * Final step: Check-in complete with wait time info.
 */

import { Button } from '@/components/ui/button';
import { CheckCircle, Clock } from 'lucide-react';

interface SuccessStepProps {
  patientName: string | undefined;
  onClose?: () => void;
}

export function SuccessStep({ patientName, onClose }: SuccessStepProps) {
  return (
    <div className="fi-stack-xl text-center">
      {/* Success Animation */}
      <div className="relative">
        <div className="w-24 h-24 mx-auto rounded-full fi-bg-card-emerald fi-flex-center animate-pulse">
          <CheckCircle className="w-12 h-12 fi-text-success" />
        </div>
        <div className="absolute inset-0 w-24 h-24 mx-auto rounded-full border-4 border-emerald-500/30 animate-ping" />
      </div>

      {/* Message */}
      <div>
        <h2 className="fi-title-2xl mb-2">¡Check-in completado!</h2>
        <p className="text-lg fi-text-success">{patientName}</p>
      </div>

      {/* Wait Info */}
      <div className="fi-card-section">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Clock className="fi-icon-lg text-indigo-400" />
          <span className="fi-title-xl">Tiempo estimado de espera</span>
        </div>
        <p className="text-4xl font-bold text-indigo-400 mb-2">~15 min</p>
        <p className="text-slate-400">Te llamaremos por tu nombre cuando sea tu turno</p>
      </div>

      {/* Tips */}
      <div className="bg-indigo-950/30 border border-indigo-600/30 rounded-xl p-4">
        <p className="text-sm text-indigo-300">
          Mantén tu celular con sonido para recibir notificaciones
        </p>
      </div>

      {/* Close Button */}
      <Button onClick={onClose} variant="secondary" size="lg" fullWidth>
        Cerrar
      </Button>
    </div>
  );
}
