"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"

export type KPIStatus = "success" | "warning" | "error" | "neutral"
export type KPITrend = "up" | "down" | "stable"

export interface KPICardProps {
  title: string
  value: string | number
  unit?: string
  status?: KPIStatus
  trend?: KPITrend
  description?: string
  icon?: React.ReactNode
  target?: string
  className?: string
}

const statusColors: Record<KPIStatus, string> = {
  success: "dash-kpi-status-success",
  warning: "dash-kpi-status-warning",
  error: "dash-kpi-status-error",
  neutral: "dash-kpi-status-neutral",
}

const trendIcons: Record<KPITrend, React.ReactNode> = {
  up: <TrendingUp className="h-4 w-4" />,
  down: <TrendingDown className="h-4 w-4" />,
  stable: <Minus className="h-4 w-4" />,
}

export function KPICard({
  title,
  value,
  unit,
  status = "neutral",
  trend,
  description,
  icon,
  target,
  className = "",
}: KPICardProps) {
  const statusColor = statusColors[status]

  return (
    <Card className={`hover:shadow-lg transition-shadow ${className}`}>
      <CardHeader className="dash-kpi-card-header">
        <CardTitle className="dash-kpi-card-title">
          {title}
        </CardTitle>
        {icon && <div className="text-slate-400">{icon}</div>}
      </CardHeader>
      <CardContent>
        <div className="dash-kpi-value-row">
          <div className={`text-3xl font-bold ${statusColor}`}>
            {value}
            {unit && <span className="text-lg ml-1">{unit}</span>}
          </div>
          {trend && (
            <div className={`flex items-center ${statusColor}`}>
              {trendIcons[trend]}
            </div>
          )}
        </div>
        {description && (
          <p className="dash-kpi-description">
            {description}
          </p>
        )}
        {target && (
          <p className="dash-kpi-target">
            Target: {target}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
