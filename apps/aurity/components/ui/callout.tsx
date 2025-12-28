/**
 * Callout Component - Unified callout styles
 *
 * DRY implementation using fi-callout-* semantic classes from AURITY Design System.
 * See: app/styles/components.css for class definitions.
 */

import React from 'react';
import { AlertCircle, CheckCircle2, Info, AlertTriangle, type LucideIcon } from 'lucide-react';

export type CalloutType = 'info' | 'warning' | 'error' | 'success';

export interface CalloutProps {
  type?: CalloutType;
  title?: string;
  className?: string;
  children: React.ReactNode;
}

const calloutConfig: Record<CalloutType, { className: string; icon: LucideIcon }> = {
  info: { className: 'fi-callout-info', icon: Info },
  warning: { className: 'fi-callout-warning', icon: AlertTriangle },
  error: { className: 'fi-callout-error', icon: AlertCircle },
  success: { className: 'fi-callout-success', icon: CheckCircle2 },
};

export function Callout({ type = 'info', title, className = '', children }: CalloutProps) {
  const config = calloutConfig[type];
  const Icon = config.icon;

  return (
    <div className={`${config.className} ${className}`}>
      <div className="fi-callout-inner">
        <Icon className="fi-callout-icon" />
        <div className="fi-callout-content">
          {title && <p className="fi-callout-title">{title}</p>}
          <div className="fi-callout-body">{children}</div>
        </div>
      </div>
    </div>
  );
}
