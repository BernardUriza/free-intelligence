/**
 * AllergyAlert Component
 *
 * Displays a single allergy alert with severity,
 * patient allergy info, and clinical notes.
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
  User,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  type AllergySeverity,
  type AllergyAlertData,
  ALLERGY_SEVERITY_LABELS,
} from "@/lib/api/prescriptions";

interface AllergyAlertProps {
  alert: AllergyAlertData;
  className?: string;
  defaultExpanded?: boolean;
  onOverride?: (alert: AllergyAlertData, justification: string) => void;
}

const SEVERITY_CONFIG: Record<
  AllergySeverity,
  {
    icon: typeof AlertTriangle;
    colors: string;
    borderColor: string;
    iconColor: string;
  }
> = {
  mild: {
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
  severe: {
    icon: XCircle,
    colors: "bg-red-50",
    borderColor: "border-red-300",
    iconColor: "text-red-600",
  },
};

export function AllergyAlert({
  alert,
  className,
  defaultExpanded = false,
  onOverride,
}: AllergyAlertProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [showOverrideInput, setShowOverrideInput] = useState(false);
  const [justification, setJustification] = useState("");

  const config = SEVERITY_CONFIG[alert.severity];
  const Icon = config.icon;
  const severityLabel = ALLERGY_SEVERITY_LABELS[alert.severity];

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
                {alert.medication}
              </span>
              <span
                className={cn(
                  "rx-alert-severity-badge",
                  config.colors,
                  config.iconColor
                )}
              >
                Alergia {severityLabel}
              </span>
            </div>
            <div className="rx-alert-patient-row">
              <User className="w-3.5 h-3.5" />
              <span>Paciente alergico a:</span>
              <span className="rx-alert-patient-value">
                {alert.patient_allergy}
              </span>
            </div>
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
          {/* Allergen Type */}
          <div className="rx-alert-allergen-row">
            <span className="rx-alert-allergen-label">Tipo de alergeno:</span>
            <span className="rx-alert-allergen-value">
              {alert.allergen_type.replace("_", " ")}
            </span>
          </div>

          {/* Clinical Notes */}
          {alert.notes && (
            <div className="rx-alert-detail-row">
              <FileText className="rx-alert-detail-icon" />
              <div>
                <span className="rx-alert-detail-label">
                  Nota Clinica
                </span>
                <p className="rx-alert-detail-value">{alert.notes}</p>
              </div>
            </div>
          )}

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
              Esta alerta no puede ser anulada - Alergia grave
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default AllergyAlert;
