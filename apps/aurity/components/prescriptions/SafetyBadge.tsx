/**
 * SafetyBadge Component
 *
 * Displays a compact badge indicating the overall safety status
 * of a prescription based on interaction and allergy checks.
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 * @card FI-RX-UI-003
 */

import { CheckCircle, AlertTriangle, XCircle, Shield } from "lucide-react";
import { cn } from "@/lib/utils";

export type SafetyStatus = "safe" | "warnings" | "blocked" | "unchecked";

interface SafetyBadgeProps {
  status: SafetyStatus;
  interactionCount?: number;
  allergyCount?: number;
  className?: string;
  size?: "sm" | "md" | "lg";
  showCounts?: boolean;
  onClick?: () => void;
}

const STATUS_CONFIG: Record<
  SafetyStatus,
  {
    icon: typeof CheckCircle;
    label: string;
    colors: string;
    description: string;
  }
> = {
  safe: {
    icon: CheckCircle,
    label: "Seguro",
    colors: "bg-green-50 text-green-700 border-green-200",
    description: "Sin alertas de seguridad",
  },
  warnings: {
    icon: AlertTriangle,
    label: "Alertas",
    colors: "bg-yellow-50 text-yellow-700 border-yellow-200",
    description: "Revisar alertas antes de continuar",
  },
  blocked: {
    icon: XCircle,
    label: "Bloqueado",
    colors: "bg-red-50 text-red-700 border-red-200",
    description: "No proceder - alertas críticas",
  },
  unchecked: {
    icon: Shield,
    label: "Sin verificar",
    colors: "bg-slate-50 text-slate-500 border-slate-200",
    description: "Ejecutar verificación de seguridad",
  },
};

const SIZE_CONFIG = {
  sm: {
    badge: "px-2 py-0.5 text-xs gap-1",
    icon: "w-3 h-3",
  },
  md: {
    badge: "px-2.5 py-1 text-sm gap-1.5",
    icon: "w-4 h-4",
  },
  lg: {
    badge: "px-3 py-1.5 text-base gap-2",
    icon: "w-5 h-5",
  },
};

export function SafetyBadge({
  status,
  interactionCount = 0,
  allergyCount = 0,
  className,
  size = "md",
  showCounts = true,
  onClick,
}: SafetyBadgeProps) {
  const config = STATUS_CONFIG[status];
  const sizeConfig = SIZE_CONFIG[size];
  const Icon = config.icon;
  const totalAlerts = interactionCount + allergyCount;

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!onClick}
      className={cn(
        "inline-flex items-center rounded-full border font-medium transition-all",
        config.colors,
        sizeConfig.badge,
        onClick && "cursor-pointer hover:opacity-80 active:scale-95",
        !onClick && "cursor-default",
        className
      )}
      title={config.description}
    >
      <Icon className={sizeConfig.icon} />
      <span>{config.label}</span>
      {showCounts && totalAlerts > 0 && (
        <span className="font-bold">({totalAlerts})</span>
      )}
    </button>
  );
}

/**
 * Determine safety status from check results
 */
export function getSafetyStatus(
  canProceed: boolean,
  hasCritical: boolean,
  alertCount: number
): SafetyStatus {
  if (!canProceed || hasCritical) return "blocked";
  if (alertCount > 0) return "warnings";
  return "safe";
}

export default SafetyBadge;
