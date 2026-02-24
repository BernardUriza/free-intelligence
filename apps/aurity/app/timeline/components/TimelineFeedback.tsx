/** Feedback states — error, empty, loading-more, end-of-feed, philosophy note. */

'use client';

import React from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

/* ---------- Error ---------- */

interface TimelineErrorProps {
  message: string;
  onRetry: () => void;
}

export function TimelineError({ message, onRetry }: TimelineErrorProps) {
  return (
    <div className="tl-error">
      <AlertCircle className="tl-error-icon fi-text-error" />
      <div className="tl-error-body">
        <p className="tl-error-text">{message}</p>
      </div>
      <Button
        onClick={onRetry}
        className="fi-btn-danger-sm"
        variant="danger"
        size="sm"
        title="Reintentar"
      >
        Reintentar
      </Button>
    </div>
  );
}

/* ---------- Empty ---------- */

export function TimelineEmpty() {
  return (
    <div className="fi-empty-state">
      <p className="tl-empty-text">Sin eventos en el período seleccionado.</p>
      <p className="tl-empty-subtext">
        &quot;No existen sesiones. Solo una conversación infinita&quot;
      </p>
    </div>
  );
}

/* ---------- Loading More ---------- */

export function TimelineLoadingMore() {
  return (
    <div className="tl-loading-more">
      <Loader2 className="tl-loading-more-spinner" />
      <span className="fi-subtitle">Cargando más eventos...</span>
    </div>
  );
}

/* ---------- End of Feed ---------- */

export function TimelineEndIndicator({ total }: { total: number }) {
  return (
    <div className="tl-end-indicator">
      <p className="fi-text-xs-muted">
        Fin de la memoria longitudinal &middot; {total} eventos totales
      </p>
    </div>
  );
}

/* ---------- Full-Page Loading ---------- */

export function TimelinePageLoading() {
  return (
    <div className="tl-page-loading">
      <div className="tl-page-loading-inner">
        <Loader2 className="tl-page-loading-spinner" />
        <p className="tl-page-loading-text">
          Cargando memoria longitudinal...
        </p>
      </div>
    </div>
  );
}

/* ---------- Philosophy ---------- */

export function TimelinePhilosophyNote() {
  return (
    <div className="tl-philosophy-note">
      <p className="fi-text-xs-muted tl-philosophy-text">
        &quot;No existen sesiones. Solo una conversación infinita&quot; —
        FI-PHIL-DOC-014
      </p>
    </div>
  );
}
