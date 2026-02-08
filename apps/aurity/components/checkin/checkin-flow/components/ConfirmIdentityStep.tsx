'use client';

/**
 * ConfirmIdentityStep Component
 *
 * Second step: Patient confirms their identity and appointment details.
 */

import { Button } from '@/components/ui/button';
import { CheckCircle, User, Calendar, ArrowLeft, ArrowRight } from 'lucide-react';
import type { IdentifyPatientResponse } from '@aurity-standalone/types/checkin';

interface ConfirmIdentityStepProps {
  patientData: IdentifyPatientResponse | null;
  onConfirm: (confirmed: boolean) => void;
}

export function ConfirmIdentityStep({ patientData, onConfirm }: ConfirmIdentityStepProps) {
  return (
    <div className="fi-stack-xl">
      {/* Header */}
      <div className="text-center">
        <div className="checkin-confirm-icon">
          <CheckCircle className="w-8 h-8 fi-text-success" />
        </div>
        <h2 className="fi-title-2xl mb-2">¿Eres tú?</h2>
        <p className="text-slate-400">Confirma que estos datos son correctos</p>
      </div>

      {/* Patient Info Card */}
      <div className="fi-card-section space-y-4">
        <div className="fi-flex-gap-lg">
          <div className="checkin-avatar-indigo">
            <User className="w-6 h-6 text-indigo-400" />
          </div>
          <div>
            <p className="fi-title">{patientData?.patient?.full_name}</p>
            {patientData?.patient?.masked_curp && (
              <p className="fi-subtitle font-mono">{patientData.patient.masked_curp}</p>
            )}
          </div>
        </div>

        <div className="pt-4 fi-border-top space-y-3">
          <div className="fi-flex-gap-md">
            <Calendar className="w-5 h-5 text-slate-500" />
            <div>
              <p className="fi-subtitle">Cita programada</p>
              <p className="text-white">
                {patientData?.appointment?.scheduled_at
                  ? new Date(patientData.appointment.scheduled_at).toLocaleString('es-MX', {
                      dateStyle: 'medium',
                      timeStyle: 'short',
                    })
                  : 'Hoy'}
              </p>
            </div>
          </div>

          <div className="fi-flex-gap-md">
            <User className="w-5 h-5 text-slate-500" />
            <div>
              <p className="fi-subtitle">Doctor</p>
              <p className="text-white">{patientData?.appointment?.doctor_name || 'Dr. Asignado'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <Button
          onClick={() => onConfirm(false)}
          variant="secondary"
          size="lg"
          fullWidth
          icon={ArrowLeft}
        >
          No soy yo
        </Button>
        <Button
          onClick={() => onConfirm(true)}
          variant="success"
          size="lg"
          fullWidth
          icon={ArrowRight}
        >
          Sí, soy yo
        </Button>
      </div>
    </div>
  );
}
