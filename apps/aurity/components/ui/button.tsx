/**
 * Button Component - Unified button styles
 *
 * DRY implementation using fi-btn-* semantic classes from AURITY Design System.
 * See: app/styles/components.css for class definitions.
 */

import * as React from "react";
import { type LucideIcon } from "lucide-react";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual style variant */
  variant?: "primary" | "secondary" | "success" | "danger" | "purple" | "indigo" | "cyan" | "ghost" | "outline" | "blue";
  /** Size preset */
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  /** Optional icon (left side) */
  icon?: LucideIcon;
  /** Icon on right side instead of left */
  iconRight?: boolean;
  /** Full width button */
  fullWidth?: boolean;
  /** Loading state (shows spinner, disables) */
  loading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({
    className,
    variant = "primary",
    size = "md",
    icon: Icon,
    iconRight = false,
    fullWidth = false,
    loading = false,
    disabled,
    children,
    ...props
  }, ref) => {
    // Semantic class mapping from fi-btn-* (components.css)
    const variantClasses: Record<string, string> = {
      primary: "fi-btn-primary",    // emerald (default brand)
      blue: "fi-btn-blue",          // blue
      secondary: "fi-btn-secondary",
      success: "fi-btn-success",    // emerald (alias)
      danger: "fi-btn-danger",
      purple: "fi-btn-purple",
      indigo: "fi-btn-indigo",
      cyan: "fi-btn-cyan",          // cyan
      ghost: "fi-btn-ghost",
      outline: "fi-btn-outline",
    };

    const sizeClasses: Record<string, string> = {
      xs: "fi-btn-xs",  // micro buttons (inline actions)
      sm: "fi-btn-sm",
      md: "",  // default size, no extra class needed
      lg: "fi-btn-lg",
      xl: "fi-btn-xl",  // CTA style with shadow/scale
    };

    const isDisabled = disabled || loading;

    // Compose semantic classes
    const classes = [
      variantClasses[variant] || "fi-btn-primary",
      sizeClasses[size],
      fullWidth ? "w-full" : "",
      className || "",
    ].filter(Boolean).join(" ");

    return (
      <button
        className={classes}
        ref={ref}
        disabled={isDisabled}
        {...props}
      >
        {loading && (
          <svg
            className="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {!loading && Icon && !iconRight && <Icon className="h-4 w-4" />}
        {children}
        {!loading && Icon && iconRight && <Icon className="h-4 w-4" />}
      </button>
    );
  }
);
Button.displayName = "Button";

export { Button };
