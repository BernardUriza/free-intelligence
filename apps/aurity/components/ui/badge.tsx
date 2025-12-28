/**
 * Badge Component - Unified badge styles
 *
 * DRY implementation using fi-badge-* semantic classes from AURITY Design System.
 * See: app/styles/components.css for class definitions.
 */

import * as React from "react"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "primary" | "warning" | "info"
}

function Badge({ className = "", variant = "default", ...props }: BadgeProps) {
  const variantClasses: Record<string, string> = {
    default: "fi-badge-primary",
    primary: "fi-badge-primary",
    secondary: "fi-badge-secondary",
    destructive: "fi-badge-danger",
    warning: "fi-badge-warning",
    info: "fi-badge-info",
    outline: "fi-badge-secondary",
  }

  return (
    <div className={`${variantClasses[variant] || "fi-badge-primary"} ${className}`} {...props} />
  )
}

export { Badge }
