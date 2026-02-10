/**
 * ClinicListSidebar Component
 *
 * Renders the left sidebar with clinic list, loading/error states, and clinic cards.
 * Single Responsibility: Clinic selection UI.
 *
 * Card: FI-CHECKIN-002
 */

import { Loader2, AlertCircle, QrCode, CreditCard, MessageSquare, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { Clinic } from '@/lib/api/clinics';

interface ClinicListSidebarProps {
  clinics: Clinic[];
  selectedClinicId: string | null;
  loading: boolean;
  error: string | null;
  onSelectClinic: (clinic: Clinic) => void;
  onRetry: () => void;
}

export function ClinicListSidebar({
  clinics,
  selectedClinicId,
  loading,
  error,
  onSelectClinic,
  onRetry,
}: ClinicListSidebarProps) {
  return (
    <div className="clinic-sidebar">
      <h2 className="fi-title mb-4">Clínicas</h2>

      {/* Loading State */}
      {loading && (
        <div className="clinic-loading">
          <Loader2 className="clinic-loading-icon" />
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="clinic-error">
          <div className="fi-flex-gap">
            <AlertCircle className="clinic-error-icon" />
            <span className="clinic-error-text">{error}</span>
          </div>
          <Button
            onClick={onRetry}
            variant="ghost"
            size="sm"
            className="clinic-retry-btn"
          >
            Reintentar
          </Button>
        </div>
      )}

      {/* Clinics List */}
      {!loading && !error && clinics.map((clinic) => (
        <div
          key={clinic.clinic_id}
          onClick={() => onSelectClinic(clinic)}
          className={`${
            selectedClinicId === clinic.clinic_id
              ? 'clinic-list-card-selected'
              : 'clinic-list-card'
          } ${!clinic.is_active ? 'clinic-list-card-inactive' : ''}`}
        >
          <div className="clinic-list-card-header">
            <div className="flex-1">
              <h3 className="clinic-list-card-name">{clinic.name}</h3>
              <p className="fi-subtitle">{clinic.specialty}</p>
              <div className="fi-flex-gap mt-2">
                {clinic.checkin_qr_enabled && (
                  <span title="QR Check-in"><QrCode className="clinic-feature-icon fi-text-green" /></span>
                )}
                {clinic.payments_enabled && (
                  <span title="Pagos"><CreditCard className="clinic-feature-icon text-yellow-400" /></span>
                )}
                {clinic.chat_enabled && (
                  <span title="Chat"><MessageSquare className="clinic-feature-icon fi-text-primary" /></span>
                )}
              </div>
            </div>
            <ChevronRight className="clinic-list-card-chevron" />
          </div>
          {!clinic.is_active && (
            <span className="clinic-inactive-label">Inactiva</span>
          )}
        </div>
      ))}

      {!loading && !error && clinics.length === 0 && (
        <div className="fi-empty-state-subtle">
          No hay clínicas registradas
        </div>
      )}
    </div>
  );
}
