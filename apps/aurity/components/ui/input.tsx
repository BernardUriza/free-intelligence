/**
 * Input Component - Unified input/textarea styles
 *
 * DRY implementation using fi-input-* semantic classes from AURITY Design System.
 * See: app/styles/components.css for class definitions.
 */

import * as React from "react";
import { type LucideIcon } from "lucide-react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  variant?: "default" | "ghost";
  icon?: LucideIcon;
  iconRight?: LucideIcon;
  error?: boolean;
  errorMessage?: string;
}

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  variant?: "default" | "ghost";
  error?: boolean;
  errorMessage?: string;
}

const variantClasses = {
  default: "fi-input",
  ghost: "fi-input-ghost",
};

const textareaVariantClasses = {
  default: "fi-textarea",
  ghost: "fi-textarea-ghost",
};

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className = "", variant = "default", icon: Icon, iconRight: IconRight, error = false, errorMessage, ...props }, ref) => {
    const inputClasses = [
      variantClasses[variant],
      error && "fi-input-error",
      Icon && "fi-input-with-icon-left",
      IconRight && "fi-input-with-icon-right",
      className,
    ].filter(Boolean).join(" ");

    return (
      <div className="fi-input-wrapper">
        {Icon && (
          <div className="fi-input-icon-left">
            <Icon className="fi-input-icon" />
          </div>
        )}
        <input ref={ref} className={inputClasses} {...props} />
        {IconRight && (
          <div className="fi-input-icon-right">
            <IconRight className="fi-input-icon" />
          </div>
        )}
        {error && errorMessage && <p className="fi-input-error-message">{errorMessage}</p>}
      </div>
    );
  }
);
Input.displayName = "Input";

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className = "", variant = "default", error = false, errorMessage, ...props }, ref) => {
    const textareaClasses = [
      textareaVariantClasses[variant],
      error && "fi-input-error",
      className,
    ].filter(Boolean).join(" ");

    return (
      <div className="fi-input-wrapper">
        <textarea ref={ref} className={textareaClasses} {...props} />
        {error && errorMessage && <p className="fi-input-error-message">{errorMessage}</p>}
      </div>
    );
  }
);
Textarea.displayName = "Textarea";

export { Input, Textarea };
