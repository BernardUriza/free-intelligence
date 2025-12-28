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
  success: "text-emerald-600 dark:fi-text-success",
  warning: "text-amber-600 dark:fi-text-warning",
  error: "text-red-600 dark:fi-text-error",
  neutral: "text-slate-600 dark:text-slate-400",
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
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-slate-600 dark:fi-text">
          {title}
        </CardTitle>
        {icon && <div className="text-slate-400">{icon}</div>}
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
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
          <p className="fi-text-xs-muted dark:text-slate-400 mt-2">
            {description}
          </p>
        )}
        {target && (
          <p className="fi-text-xs dark:text-slate-500 mt-1">
            Target: {target}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
