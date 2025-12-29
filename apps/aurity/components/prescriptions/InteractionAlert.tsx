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
                {alert.drug_1}
              </span>
              <span className="text-slate-400">+</span>
              <span className="font-semibold text-slate-800">
                {alert.drug_2}
              </span>
              <span
                className={cn(
                  "text-xs font-medium px-1.5 py-0.5 rounded",
                  config.colors,
                  config.iconColor
                )}
              >
                {severityLabel}
              </span>
            </div>
            <p className="text-sm text-slate-600 mt-0.5">{alert.effect}</p>
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
          {/* Recommendation */}
          <div className="flex items-start gap-2">
            <Pill className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
            <div>
              <span className="text-xs font-medium text-slate-500 uppercase">
                Recomendación
              </span>
              <p className="text-sm text-slate-700">{alert.recommendation}</p>
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
              Esta alerta no puede ser anulada
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default InteractionAlert;
