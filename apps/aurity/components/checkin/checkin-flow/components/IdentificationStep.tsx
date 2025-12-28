'use client';

/**
 * IdentificationStep Component
 *
 * First step: Patient identifies via code, CURP, or name/DOB.
 */

import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { User, AlertCircle, ArrowRight, Hash, CreditCard, X } from 'lucide-react';
import { formatCheckinCode } from '@aurity-standalone/api-client/checkin';
import type { IdentificationMethod, IdentificationFormState } from '../types';

interface IdentificationStepProps {
  clinicName: string;
  method: IdentificationMethod;
  formState: IdentificationFormState;
  error: string | null;
  isLoading: boolean;
  onMethodChange: (method: IdentificationMethod) => void;
  onFormChange: (field: keyof IdentificationFormState, value: string) => void;
  onSubmit: () => void;
  onCancel?: () => void;
}

export function IdentificationStep({
  clinicName,
  method,
  formState,
  error,
  isLoading,
  onMethodChange,
  onFormChange,
  onSubmit,
  onCancel,
}: IdentificationStepProps) {
  return (
    <div className="fi-stack-xl">
      {/* Header */}
      <div className="text-center">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full fi-bg-card-purple fi-flex-center">
          <User className="fi-icon-xl text-indigo-400" />
        </div>
        <h2 className="fi-title-2xl mb-2">Check-in</h2>
        <p className="text-slate-400">Bienvenido a {clinicName}</p>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-950/30 border border-red-500/30 rounded-lg">
          <AlertCircle className="w-5 h-5 fi-text-error flex-shrink-0" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Method Selector */}
      <div className="grid grid-cols-3 gap-2">
        {(['code', 'curp', 'name_dob'] as const).map((m) => (
          <Button
            key={m}
            onClick={() => onMethodChange(m)}
            className={method === m ? 'fi-tab-pill-active' : 'fi-tab-pill'}
            variant={method === m ? 'primary' : 'ghost'}
            size="sm"
            type="button"
            aria-pressed={method === m}
          >
            {m === 'code' && 'Código'}
            {m === 'curp' && 'CURP'}
            {m === 'name_dob' && 'Nombre'}
          </Button>
        ))}
      </div>

      {/* Identification Forms */}
      <div className="space-y-4">
        {method === 'code' && (
          <div>
            <label className="fi-label">Código de cita (6 dígitos)</label>
            <Input
              type="text"
              value={formState.checkinCode}
              onChange={(e) => {
                const value = e.target.value.replace(/[^0-9]/g, '').slice(0, 6);
                onFormChange('checkinCode', formatCheckinCode(value));
              }}
              placeholder="123-456"
              icon={Hash}
              className="py-3 text-center text-2xl tracking-widest font-mono"
              maxLength={7}
            />
            <p className="fi-text-xs-muted mt-2">
              Lo recibiste por SMS o email al agendar tu cita
            </p>
          </div>
        )}

        {method === 'curp' && (
          <div>
            <label className="fi-label">CURP</label>
            <Input
              type="text"
              value={formState.curp}
              onChange={(e) => onFormChange('curp', e.target.value.toUpperCase().slice(0, 18))}
              placeholder="GARM850101HDFRRL09"
              icon={CreditCard}
              className="py-3 font-mono"
              maxLength={18}
            />
          </div>
        )}

        {method === 'name_dob' && (
          <>
            <div>
              <label className="fi-label">Nombre(s)</label>
              <Input
                type="text"
                value={formState.firstName}
                onChange={(e) => onFormChange('firstName', e.target.value)}
                placeholder="María"
                className="py-3"
              />
            </div>
            <div>
              <label className="fi-label">Apellidos</label>
              <Input
                type="text"
                value={formState.lastName}
                onChange={(e) => onFormChange('lastName', e.target.value)}
                placeholder="García Ramírez"
                className="py-3"
              />
            </div>
            <div>
              <label className="fi-label">Fecha de nacimiento</label>
              <Input
                type="date"
                value={formState.dateOfBirth}
                onChange={(e) => onFormChange('dateOfBirth', e.target.value)}
                className="py-3"
              />
            </div>
          </>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        {onCancel && (
          <Button onClick={onCancel} variant="secondary" size="lg" fullWidth icon={X}>
            Cancelar
          </Button>
        )}
        <Button
          onClick={onSubmit}
          disabled={isLoading}
          loading={isLoading}
          variant="indigo"
          size="lg"
          fullWidth
          icon={ArrowRight}
        >
          Continuar
        </Button>
      </div>
    </div>
  );
}
