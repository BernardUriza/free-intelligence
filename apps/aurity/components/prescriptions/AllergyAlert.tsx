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
        "rounded-lg border-l-4 p-3",
        config.colors,
        config.borderColor,
        className
      )}
    >
      {/* Header */}
      <div
        className="flex items-start justify-between cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-start gap-2">
          <Icon className={cn("w-5 h-5 mt-0.5 flex-shrink-0", config.iconColor)} />
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-slate-800">
                {alert.medication}
              </span>
              <span
                className={cn(
                  "text-xs font-medium px-1.5 py-0.5 rounded",
                  config.colors,
                  config.iconColor
                )}
              >
                Alergia {severityLabel}
              </span>
            </div>
            <div className="flex items-center gap-1 mt-0.5 text-sm text-slate-600">
              <User className="w-3.5 h-3.5" />
              <span>Paciente alérgico a:</span>
              <span className="font-medium text-slate-700">
                {alert.patient_allergy}
              </span>
            </div>
          </div>
        </div>
        <button
          type="button"
          className="p-1 hover:bg-white/50 rounded transition-colors"
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
        <div className="mt-3 pt-3 border-t border-slate-200/50 space-y-3">
          {/* Allergen Type */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-500">Tipo de alérgeno:</span>
            <span className="font-medium text-slate-700 capitalize">
              {alert.allergen_type.replace("_", " ")}
            </span>
          </div>

          {/* Clinical Notes */}
          {alert.notes && (
            <div className="flex items-start gap-2">
              <FileText className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
              <div>
                <span className="text-xs font-medium text-slate-500 uppercase">
                  Nota Clínica
                </span>
                <p className="text-sm text-slate-700">{alert.notes}</p>
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
                  className="text-xs text-slate-500 hover:text-slate-700 underline"
                >
                  Anular alerta con justificación
                </button>
              ) : (
                <div className="space-y-2" onClick={(e) => e.stopPropagation()}>
                  <textarea
                    value={justification}
                    onChange={(e) => setJustification(e.target.value)}
                    placeholder="Justificación clínica para anular esta alerta (mín. 10 caracteres)..."
                    className="w-full text-sm p-2 border border-slate-300 rounded resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={2}
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={handleOverride}
                      disabled={justification.trim().length < 10}
                      className="text-xs px-3 py-1 bg-orange-500 text-white rounded hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Confirmar Anulación
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setShowOverrideInput(false);
                        setJustification("");
                      }}
                      className="text-xs px-3 py-1 text-slate-600 hover:text-slate-800"
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
            <div className="flex items-center gap-1.5 text-xs text-red-600 font-medium">
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
