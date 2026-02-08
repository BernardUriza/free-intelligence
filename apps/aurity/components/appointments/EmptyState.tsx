/**
 * Empty State Component
 * Card: FI-CHECKIN-005 (Phase 2)
 *
 * Displayed when no doctors are configured for the selected clinic.
 */

import Link from 'next/link';
import { Calendar, ArrowRight } from 'lucide-react';

export function EmptyState() {
  return (
    <div className="apt-empty">
      <div className="apt-empty-content">
        <Calendar className="apt-empty-icon" />
        <h3 className="apt-empty-title">
          No hay doctores configurados
        </h3>
        <p className="apt-empty-description">
          Agregue doctores en la sección de Clínicas para ver la agenda
        </p>
        <Link
          href="/admin/clinics"
          className="apt-empty-action"
        >
          Configurar Clínicas
          <ArrowRight className="apt-empty-action-icon" />
        </Link>
      </div>
    </div>
  );
}
