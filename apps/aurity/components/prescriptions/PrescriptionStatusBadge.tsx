/**
 * PrescriptionStatusBadge Component
 *
 * Displays the current status of a prescription with appropriate styling.
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 */

import { Badge } from "@/components/ui/badge";
import {
  PrescriptionStatus,
  STATUS_LABELS,
} from "@/lib/api/prescriptions";
import {
  FileEdit,
  Clock,
  CheckCircle,
  PackageCheck,
  XCircle,
  AlertTriangle,
} from "lucide-react";

interface PrescriptionStatusBadgeProps {
  status: PrescriptionStatus;
  showIcon?: boolean;
  size?: "sm" | "md" | "lg";
}

const STATUS_CONFIG: Record<
  PrescriptionStatus,
  { color: string; icon: React.ElementType; bgClass: string }
> = {
  draft: {
    color: "text-slate-400",
    icon: FileEdit,
    bgClass: "bg-slate-100 dark:bg-slate-800",
  },
  pending_signature: {
    color: "text-amber-500",
    icon: Clock,
    bgClass: "bg-amber-100 dark:bg-amber-900/30",
  },
  signed: {
    color: "text-green-500",
    icon: CheckCircle,
    bgClass: "bg-green-100 dark:bg-green-900/30",
  },
  dispensed: {
    color: "text-blue-500",
    icon: PackageCheck,
    bgClass: "bg-blue-100 dark:bg-blue-900/30",
  },
  cancelled: {
    color: "text-red-500",
    icon: XCircle,
    bgClass: "bg-red-100 dark:bg-red-900/30",
  },
  expired: {
    color: "text-orange-500",
    icon: AlertTriangle,
    bgClass: "bg-orange-100 dark:bg-orange-900/30",
  },
};

const SIZE_CLASSES = {
  sm: "text-xs px-2 py-0.5",
  md: "text-sm px-2.5 py-1",
  lg: "text-base px-3 py-1.5",
};

const ICON_SIZES = {
  sm: "w-3 h-3",
  md: "w-4 h-4",
  lg: "w-5 h-5",
};

export function PrescriptionStatusBadge({
  status,
  showIcon = true,
  size = "md",
}: PrescriptionStatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;
  const label = STATUS_LABELS[status];

  return (
    <Badge
      variant="outline"
      className={`${config.bgClass} ${config.color} ${SIZE_CLASSES[size]} inline-flex items-center gap-1.5 font-medium border-0`}
    >
      {showIcon && <Icon className={ICON_SIZES[size]} />}
      <span>{label}</span>
    </Badge>
  );
}
