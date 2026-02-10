/**
 * InteractionAlert Component
 *
 * Displays a single drug-drug interaction alert with severity,
 * effect description, and recommendation.
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 * @card FI-RX-UI-003
 */

import { useState } from "react";
import {
  AlertTriangle,
  XCircle,
  Info,
  ChevronDown,
  ChevronUp,
  Pill,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  type InteractionSeverity,
  type InteractionAlertData,
  INTERACTION_SEVERITY_LABELS,
} from "@/lib/api/prescriptions";

interface InteractionAlertProps {
  alert: InteractionAlertData;
  className?: string;
  defaultExpanded?: boolean;
  onOverride?: (alert: InteractionAlertData, justification: string) => void;
}

const SEVERITY_CONFIG: Record<
  InteractionSeverity,
  {
    icon: typeof AlertTriangle;
    colors: string;
    borderColor: string;
    iconColor: string;
  }
> = {
  minor: {
    icon: Info,
    colors: "bg-blue-50",
    borderColor: "border-blue-200",
    iconColor: "text-blue-500",
  },
  moderate: {
    icon: AlertTriangle,
    colors: "bg-yellow-50",
    borderColor: "border-yellow-300",
    iconColor: "text-yellow-600",
  },
  major: {
    icon: AlertTriangle,
    colors: "bg-orange-50",
    borderColor: "border-orange-300",
    iconColor: "text-orange-600",
  },
  contraindicated: {
    icon: XCircle,
    colors: "bg-red-50",
    borderColor: "border-red-300",
    iconColor: "text-red-600",
  },
};

export function InteractionAlert({
  alert,
  className,
  defaultExpanded = false,
  onOverride,
}: InteractionAlertProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [showOverrideInput, setShowOverrideInput] = useState(false);
  const [justification, setJustification] = useState("");

  const config = SEVERITY_CONFIG[alert.severity];
  const Icon = config.icon;
  const severityLabel = INTERACTION_SEVERITY_LABELS[alert.severity];

  const handleOverride = () => {
    if (justification.trim().length >= 10 && onOverride) {
      onOverride(alert, justification);
      setShowOverrideInput(false);
      setJustification("");
    }
  };

  return (
    <div
      className={cn(
        "rx-alert-card",
        config.colors,
        config.borderColor,
        className
      )}
    >
      {/* Header */}
      <div
        className="rx-alert-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="rx-alert-header-left">
          <Icon className={cn("rx-alert-icon", config.iconColor)} />
          <div>
            <div className="rx-alert-title-row">
              <span className="rx-alert-drug-name">
                {alert.drug_1}
              </span>
              <span className="text-slate-400">+</span>
              <span className="rx-alert-drug-name">
                {alert.drug_2}
              </span>
              <span
                className={cn(
                  "rx-alert-severity-badge",
                  config.colors,
                  config.iconColor
                )}
              >
                {severityLabel}
              </span>
            </div>
            <p className="rx-alert-effect">{alert.effect}</p>
          </div>
        </div>
        <button
          type="button"
          className="rx-alert-toggle"
        >
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </button>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="rx-alert-body">
          {/* Recommendation */}
          <div className="rx-alert-detail-row">
            <Pill className="rx-alert-detail-icon" />
            <div>
              <span className="rx-alert-detail-label">
                Recomendacion
              </span>
              <p className="rx-alert-detail-value">{alert.recommendation}</p>
            </div>
          </div>

          {/* Override Section */}
          {alert.can_override && onOverride && (
            <div className="pt-2">
              {!showOverrideInput ? (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowOverrideInput(true);
                  }}
                  className="rx-alert-override-link"
                >
                  Anular alerta con justificacion
                </button>
              ) : (
                <div className="space-y-2" onClick={(e) => e.stopPropagation()}>
                  <textarea
                    value={justification}
                    onChange={(e) => setJustification(e.target.value)}
                    placeholder="Justificacion clinica para anular esta alerta (min. 10 caracteres)..."
                    className="rx-alert-override-textarea"
                    rows={2}
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={handleOverride}
                      disabled={justification.trim().length < 10}
                      className="rx-alert-override-confirm"
                    >
                      Confirmar Anulacion
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setShowOverrideInput(false);
                        setJustification("");
                      }}
                      className="rx-alert-override-cancel"
                    >
                      Cancelar
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Non-overridable warning */}
          {!alert.can_override && (
            <div className="rx-alert-no-override">
              <XCircle className="w-3.5 h-3.5" />
              Esta alerta no puede ser anulada
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default InteractionAlert;
