'use client';

/**
 * PendingActionsStep Component
 *
 * Third step: Patient completes required actions before check-in.
 */

import { Button } from '@/components/ui/button';
import { AlertCircle, CheckCircle, ArrowLeft } from 'lucide-react';
import { getActionIcon } from '@aurity-standalone/api-client/checkin';
import type { PendingAction } from '@aurity-standalone/types/checkin';

interface PendingActionsStepProps {
  actions: PendingAction[];
  error: string | null;
  isLoading: boolean;
  canProceed: boolean;
  onCompleteAction: (actionId: string) => void;
  onSkipAction: (actionId: string) => void;
  onBack: () => void;
  onComplete: () => void;
}

export function PendingActionsStep({
  actions,
  error,
  isLoading,
  canProceed,
  onCompleteAction,
  onSkipAction,
  onBack,
  onComplete,
}: PendingActionsStepProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <h2 className="fi-title-2xl mb-2">Antes de continuar</h2>
        <p className="text-slate-400">Completa estas acciones para finalizar tu check-in</p>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-950/30 border border-red-500/30 rounded-lg">
          <AlertCircle className="w-5 h-5 fi-text-error flex-shrink-0" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Actions List */}
      <div className="fi-stack-md">
        {actions.map((action) => (
          <div
            key={action.action_id}
            className={
              action.status === 'completed'
                ? 'fi-action-card-complete'
                : action.status === 'skipped'
                ? 'fi-action-card-skipped'
                : 'fi-action-card'
            }
          >
            <div className="flex items-start gap-4">
              {/* Icon */}
              <div
                className={
                  action.status === 'completed' ? 'fi-action-icon-box-complete' : 'fi-action-icon-box'
                }
              >
                <span className="text-xl">{getActionIcon(action.action_type)}</span>
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="fi-flex-gap">
                  <p className="font-medium text-white">{action.title}</p>
                  {action.is_required && action.status === 'pending' && (
                    <span className="px-2 py-0.5 bg-red-500/20 fi-text-error text-xs rounded">
                      Requerido
                    </span>
                  )}
                  {action.status === 'completed' && (
                    <CheckCircle className="w-4 h-4 fi-text-success" />
                  )}
                </div>
                {action.description && <p className="fi-subtitle mt-1">{action.description}</p>}
                {action.amount && (
                  <p className="fi-title mt-2">
                    ${action.amount.toLocaleString()} {action.currency || 'MXN'}
                  </p>
                )}
              </div>

              {/* Action Buttons */}
              {action.status === 'pending' && (
                <div className="flex gap-2">
                  {!action.is_required && (
                    <Button
                      onClick={() => onSkipAction(action.action_id)}
                      disabled={isLoading}
                      variant="ghost"
                      size="sm"
                    >
                      Omitir
                    </Button>
                  )}
                  <Button
                    onClick={() => onCompleteAction(action.action_id)}
                    disabled={isLoading}
                    variant="indigo"
                    size="sm"
                  >
                    {action.action_type.startsWith('pay_') ? 'Pagar' : 'Completar'}
                  </Button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <Button onClick={onBack} variant="secondary" size="lg" fullWidth icon={ArrowLeft}>
          Atrás
        </Button>
        <Button
          onClick={onComplete}
          disabled={!canProceed || isLoading}
          loading={isLoading}
          variant="success"
          size="lg"
          fullWidth
          icon={CheckCircle}
        >
          Completar Check-in
        </Button>
      </div>
    </div>
  );
}
