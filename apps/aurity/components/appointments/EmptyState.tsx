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
    <div className="flex items-center justify-center min-h-[400px] bg-slate-900/50 rounded-lg border border-slate-700/50">
      <div className="text-center">
        <Calendar className="h-16 w-16 text-slate-600 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-slate-200">
          No hay doctores configurados
        </h3>
        <p className="text-slate-400 mt-1 mb-4">
          Agregue doctores en la sección de Clínicas para ver la agenda
        </p>
        <Link
          href="/admin/clinics"
          className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          Configurar Clínicas
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}
