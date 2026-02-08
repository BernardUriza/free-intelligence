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
    <div className={cn("safety-panel", className)}>
      {/* Header */}
      <div className="safety-header">
        <div className="safety-header-left">
          <Shield className="safety-header-icon" />
          <div>
            <h3 className="safety-header-title">
              Verificación de Seguridad
            </h3>
            {safetyCheck && (
              <p className="safety-header-summary">{safetyCheck.summary}</p>
            )}
          </div>
        </div>
        <div className="safety-header-right">
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
              className={isLoading
                ? "safety-refresh-btn-disabled"
                : "safety-refresh-btn-enabled"
              }
              title="Ejecutar verificación"
            >
              <RefreshCw
                className={cn("safety-refresh-icon", isLoading && "safety-spinning")}
              />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="safety-content">
        {/* Loading State */}
        {isLoading && (
          <div className="safety-loading">
            <RefreshCw className="safety-loading-icon" />
            <span>Verificando seguridad...</span>
          </div>
        )}

        {/* Error State */}
        {error && !isLoading && (
          <div className="safety-error">
            <AlertCircle className="safety-error-icon" />
            <div>
              <p className="safety-error-title">Error en verificación</p>
              <p className="safety-error-message">{error}</p>
            </div>
          </div>
        )}

        {/* Unchecked State */}
        {!safetyCheck && !isLoading && !error && (
          <div className="safety-unchecked">
            <Shield className="safety-unchecked-icon" />
            <p className="safety-unchecked-text">
              Aún no se ha ejecutado la verificación de seguridad
            </p>
            {onRunCheck && (
              <button
                type="button"
                onClick={onRunCheck}
                className="safety-unchecked-btn"
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
              <div className="safety-clear">
                <Shield className="safety-clear-icon" />
                <p className="safety-clear-title">Sin alertas de seguridad</p>
                <p className="safety-clear-subtitle">
                  Los medicamentos son compatibles y no hay alergias detectadas
                </p>
              </div>
            )}

            {/* Interaction Alerts Section */}
            {interactionAlerts.length > 0 && (
              <div className="safety-section-stack">
                <button
                  type="button"
                  onClick={() => setInteractionsExpanded(!interactionsExpanded)}
                  className="safety-section-toggle"
                >
                  <div className="safety-section-label-row">
                    <span className="safety-section-label">
                      Interacciones Medicamentosas
                    </span>
                    <span className="safety-section-count-interaction">
                      {interactionAlerts.length}
                    </span>
                  </div>
                  {interactionsExpanded ? (
                    <ChevronUp className="safety-chevron" />
                  ) : (
                    <ChevronDown className="safety-chevron" />
                  )}
                </button>

                {interactionsExpanded && (
                  <div className="safety-section-body">
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
              <div className="safety-section-stack">
                <button
                  type="button"
                  onClick={() => setAllergiesExpanded(!allergiesExpanded)}
                  className="safety-section-toggle"
                >
                  <div className="safety-section-label-row">
                    <span className="safety-section-label">
                      Alertas de Alergia
                    </span>
                    <span className="safety-section-count-allergy">
                      {allergyAlerts.length}
                    </span>
                  </div>
                  {allergiesExpanded ? (
                    <ChevronUp className="safety-chevron" />
                  ) : (
                    <ChevronDown className="safety-chevron" />
                  )}
                </button>

                {allergiesExpanded && (
                  <div className="safety-section-body">
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
              <div className="safety-banner-blocked">
                <p className="safety-banner-blocked-title">
                  <AlertTriangle className="safety-banner-icon" strokeWidth={1.5} aria-hidden="true" />
                  No se puede proceder con la receta
                </p>
                <p className="safety-banner-blocked-desc">
                  Existen alertas críticas que requieren atención. Revise las
                  alertas y anule con justificación clínica si es necesario.
                </p>
              </div>
            )}

            {safetyCheck.can_proceed && totalAlerts > 0 && (
              <div className="safety-banner-caution">
                <p className="safety-banner-caution-title">
                  <Zap className="safety-banner-icon" strokeWidth={1.5} aria-hidden="true" />
                  Proceder con precaución
                </p>
                <p className="safety-banner-caution-desc">
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
