/**
 * SafetyAlerts Component
 *
 * Consolidated panel displaying all safety alerts (interactions + allergies)
 * with summary badge and expandable details.
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 * @card FI-RX-UI-003
 */

import { useState } from "react";
import {
  Shield,
  RefreshCw,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  type SafetyCheckResponse,
  type InteractionAlertData,
  type AllergyAlertData,
} from "@/lib/api/prescriptions";
import { SafetyBadge, getSafetyStatus, type SafetyStatus } from "./SafetyBadge";
import { InteractionAlert } from "./InteractionAlert";
import { AllergyAlert } from "./AllergyAlert";

interface SafetyAlertsProps {
  /** Safety check response from API */
  safetyCheck: SafetyCheckResponse | null;
  /** Loading state while checking */
  isLoading?: boolean;
  /** Error message if check failed */
  error?: string | null;
  /** Callback to run safety check */
  onRunCheck?: () => void;
  /** Callback when an interaction alert is overridden */
  onOverrideInteraction?: (
    alert: InteractionAlertData,
    justification: string
  ) => void;
  /** Callback when an allergy alert is overridden */
  onOverrideAllergy?: (alert: AllergyAlertData, justification: string) => void;
  /** Custom class name */
  className?: string;
  /** Collapse sections by default */
  defaultCollapsed?: boolean;
}

export function SafetyAlerts({
  safetyCheck,
  isLoading = false,
  error = null,
  onRunCheck,
  onOverrideInteraction,
  onOverrideAllergy,
  className,
  defaultCollapsed = false,
}: SafetyAlertsProps) {
  const [interactionsExpanded, setInteractionsExpanded] =
    useState(!defaultCollapsed);
  const [allergiesExpanded, setAllergiesExpanded] = useState(!defaultCollapsed);

  // Calculate status
  const status: SafetyStatus = safetyCheck
    ? getSafetyStatus(
        safetyCheck.can_proceed,
        safetyCheck.has_critical_issues,
        (safetyCheck.interactions?.alerts?.length || 0) +
          (safetyCheck.allergies?.alerts?.length || 0)
      )
    : "unchecked";

  const interactionAlerts = safetyCheck?.interactions?.alerts || [];
  const allergyAlerts = safetyCheck?.allergies?.alerts || [];
  const totalAlerts = interactionAlerts.length + allergyAlerts.length;

  return (
    <div className={cn("rounded-lg border border-slate-200 bg-white", className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <Shield className="w-5 h-5 text-slate-400" />
          <div>
            <h3 className="font-semibold text-slate-800">
              Verificación de Seguridad
            </h3>
            {safetyCheck && (
              <p className="text-sm text-slate-500">{safetyCheck.summary}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <SafetyBadge
            status={status}
            interactionCount={interactionAlerts.length}
            allergyCount={allergyAlerts.length}
            size="md"
          />
          {onRunCheck && (
            <button
              type="button"
              onClick={onRunCheck}
              disabled={isLoading}
              className={cn(
                "p-2 rounded-lg transition-colors",
                isLoading
                  ? "bg-slate-100 text-slate-400 cursor-not-allowed"
                  : "hover:bg-slate-100 text-slate-600"
              )}
              title="Ejecutar verificación"
            >
              <RefreshCw
                className={cn("w-4 h-4", isLoading && "animate-spin")}
              />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-8 text-slate-500">
            <RefreshCw className="w-5 h-5 animate-spin mr-2" />
            <span>Verificando seguridad...</span>
          </div>
        )}

        {/* Error State */}
        {error && !isLoading && (
          <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Error en verificación</p>
              <p className="text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Unchecked State */}
        {!safetyCheck && !isLoading && !error && (
          <div className="text-center py-6">
            <Shield className="w-12 h-12 text-slate-300 mx-auto mb-2" />
            <p className="text-slate-500 mb-3">
              Aún no se ha ejecutado la verificación de seguridad
            </p>
            {onRunCheck && (
              <button
                type="button"
                onClick={onRunCheck}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
              >
                Verificar Ahora
              </button>
            )}
          </div>
        )}

        {/* Results */}
        {safetyCheck && !isLoading && (
          <>
            {/* No Alerts */}
            {totalAlerts === 0 && (
              <div className="text-center py-6 text-green-600">
                <Shield className="w-12 h-12 mx-auto mb-2" />
                <p className="font-medium">Sin alertas de seguridad</p>
                <p className="text-sm text-slate-500">
                  Los medicamentos son compatibles y no hay alergias detectadas
                </p>
              </div>
            )}

            {/* Interaction Alerts Section */}
            {interactionAlerts.length > 0 && (
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => setInteractionsExpanded(!interactionsExpanded)}
                  className="flex items-center justify-between w-full p-2 rounded-lg hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-700">
                      Interacciones Medicamentosas
                    </span>
                    <span className="text-xs px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded-full">
                      {interactionAlerts.length}
                    </span>
                  </div>
                  {interactionsExpanded ? (
                    <ChevronUp className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  )}
                </button>

                {interactionsExpanded && (
                  <div className="space-y-2 pl-2">
                    {interactionAlerts.map((alert, index) => (
                      <InteractionAlert
                        key={`${alert.drug_1}-${alert.drug_2}-${index}`}
                        alert={alert}
                        onOverride={onOverrideInteraction}
                        defaultExpanded={
                          alert.severity === "contraindicated" ||
                          alert.severity === "major"
                        }
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Allergy Alerts Section */}
            {allergyAlerts.length > 0 && (
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => setAllergiesExpanded(!allergiesExpanded)}
                  className="flex items-center justify-between w-full p-2 rounded-lg hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-700">
                      Alertas de Alergia
                    </span>
                    <span className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded-full">
                      {allergyAlerts.length}
                    </span>
                  </div>
                  {allergiesExpanded ? (
                    <ChevronUp className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  )}
                </button>

                {allergiesExpanded && (
                  <div className="space-y-2 pl-2">
                    {allergyAlerts.map((alert, index) => (
                      <AllergyAlert
                        key={`${alert.medication}-${alert.patient_allergy}-${index}`}
                        alert={alert}
                        onOverride={onOverrideAllergy}
                        defaultExpanded={alert.severity === "severe"}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Action Guidance */}
            {!safetyCheck.can_proceed && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-700 font-medium flex items-center gap-1">
                  <AlertTriangle className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />
                  No se puede proceder con la receta
                </p>
                <p className="text-xs text-red-600 mt-1">
                  Existen alertas críticas que requieren atención. Revise las
                  alertas y anule con justificación clínica si es necesario.
                </p>
              </div>
            )}

            {safetyCheck.can_proceed && totalAlerts > 0 && (
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm text-yellow-700 font-medium flex items-center gap-1">
                  <Zap className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />
                  Proceder con precaución
                </p>
                <p className="text-xs text-yellow-600 mt-1">
                  Hay alertas que deben revisarse antes de continuar. La receta
                  puede generarse después de revisar las alertas.
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default SafetyAlerts;
