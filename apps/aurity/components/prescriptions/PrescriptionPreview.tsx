/**
 * PrescriptionPreview Component
 *
 * Displays a print-ready preview of a prescription.
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 */

"use client";

import { forwardRef } from "react";
import { AlertTriangle } from "lucide-react";
import {
  Prescription,
  FREQUENCY_LABELS,
  ROUTE_LABELS,
} from "@/lib/api/prescriptions";
import { PrescriptionStatusBadge } from "./PrescriptionStatusBadge";
// Simple Separator component (inline)
const Separator = ({ className = "" }: { className?: string }) => (
  <hr className={`rx-prev-separator ${className}`} />
);

interface PrescriptionPreviewProps {
  prescription: Prescription;
  showHeader?: boolean;
  showFooter?: boolean;
  className?: string;
}

export const PrescriptionPreview = forwardRef<
  HTMLDivElement,
  PrescriptionPreviewProps
>(function PrescriptionPreview(
  { prescription, showHeader = true, showFooter = true, className = "" },
  ref
) {
  const { patient, physician, medications, diagnosis } = prescription;

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("es-MX", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  };

  return (
    <div
      ref={ref}
      className={`rx-prev-page ${className}`}
      style={{ minHeight: "297mm" }}
    >
      {/* Header / Membrete */}
      {showHeader && (
        <header className="rx-prev-header">
          {physician.institution && (
            <h1 className="rx-prev-institution">
              {physician.institution}
            </h1>
          )}
          <h2 className="rx-prev-physician-name">
            Dr(a). {physician.name}
          </h2>
          {physician.specialty && (
            <p className="rx-prev-specialty">{physician.specialty}</p>
          )}
          <p className="rx-prev-license">
            Cédula Profesional: {physician.professional_license}
          </p>
          {physician.specialty_license && (
            <p className="rx-prev-license-secondary">
              Cédula de Especialidad: {physician.specialty_license}
            </p>
          )}
          {physician.address && (
            <p className="rx-prev-address">{physician.address}</p>
          )}
          {physician.phone && (
            <p className="rx-prev-phone">Tel: {physician.phone}</p>
          )}
        </header>
      )}

      <Separator className="rx-prev-divider" />

      {/* Title */}
      <div className="rx-prev-title-section">
        <h2 className="rx-prev-title">RECETA MÉDICA</h2>
        <div className="rx-prev-status-row">
          <PrescriptionStatusBadge status={prescription.status} size="sm" />
        </div>
      </div>

      {/* Patient Info */}
      <section className="rx-prev-patient-grid">
        <div>
          <span className="rx-prev-field-label">Paciente:</span> {patient.name}
        </div>
        <div>
          <span className="rx-prev-field-label">Fecha:</span>{" "}
          {formatDate(prescription.created_at)}
        </div>
        {patient.age && (
          <div>
            <span className="rx-prev-field-label">Edad:</span> {patient.age}
          </div>
        )}
        {patient.weight_kg && (
          <div>
            <span className="rx-prev-field-label">Peso:</span> {patient.weight_kg} kg
          </div>
        )}
        {patient.allergies.length > 0 && (
          <div className="rx-prev-allergies">
            <span className="rx-prev-field-label">Alergias:</span>{" "}
            {patient.allergies.join(", ")}
          </div>
        )}
      </section>

      {/* Diagnosis */}
      <section className="rx-prev-section">
        <h3 className="rx-prev-section-heading">
          Diagnóstico
        </h3>
        <p className="rx-prev-section-text">{diagnosis}</p>
        {prescription.diagnosis_code && (
          <p className="rx-prev-diagnosis-code">
            CIE-10: {prescription.diagnosis_code}
          </p>
        )}
      </section>

      <Separator className="rx-prev-divider-dashed" />

      {/* Medications */}
      <section className="rx-prev-section">
        <h3 className="rx-prev-section-heading-meds">
          Medicamentos
        </h3>
        <div className="rx-prev-med-stack">
          {medications.map((med, index) => {
            const frequencyLabel =
              med.frequency === "custom" && med.frequency_custom
                ? med.frequency_custom
                : FREQUENCY_LABELS[med.frequency];
            const routeLabel = ROUTE_LABELS[med.route];
            const durationLabel = med.duration_text
              ? med.duration_text
              : med.duration_days
              ? `${med.duration_days} días`
              : "Según indicación";

            return (
              <div key={index} className="rx-prev-med-item">
                <p className="rx-prev-med-name">
                  {index + 1}. Rx: {med.name}
                  {med.active_ingredient &&
                    med.active_ingredient !== med.name &&
                    ` (${med.active_ingredient})`}
                </p>
                <p className="rx-prev-med-detail">
                  {med.dosage} - {med.dosage_form}
                </p>
                <p className="rx-prev-med-detail">
                  {routeLabel}, {frequencyLabel}
                </p>
                <p className="rx-prev-med-detail">Duración: {durationLabel}</p>
                {med.quantity && (
                  <p className="rx-prev-med-quantity">Cantidad: {med.quantity}</p>
                )}
                {med.instructions && (
                  <p className="rx-prev-med-instructions">
                    Indicaciones: {med.instructions}
                  </p>
                )}
                {med.warnings && (
                  <p className="rx-prev-med-warning">
                    <AlertTriangle className="rx-prev-med-warning-icon" strokeWidth={1.5} aria-hidden="true" />
                    {med.warnings}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* General Instructions */}
      {prescription.general_instructions && (
        <section className="rx-prev-section">
          <h3 className="rx-prev-section-heading">
            Indicaciones Generales
          </h3>
          <p className="rx-prev-section-text-pre">
            {prescription.general_instructions}
          </p>
        </section>
      )}

      {/* Next Appointment */}
      {prescription.next_appointment && (
        <section className="rx-prev-section">
          <p className="rx-prev-appointment">
            <span className="rx-prev-field-label">Próxima cita:</span>{" "}
            {prescription.next_appointment}
          </p>
        </section>
      )}

      {/* Footer */}
      {showFooter && (
        <footer className="rx-prev-footer">
          <Separator className="rx-prev-footer-separator" />

          <div className="rx-prev-footer-layout">
            <div className="rx-prev-footer-meta">
              {prescription.signature_hash && (
                <p>Verificación: {prescription.signature_hash.slice(0, 16)}...</p>
              )}
              <p>
                Válida por {prescription.validity_days} días a partir de la
                fecha de emisión
              </p>
            </div>

            <div className="rx-prev-footer-signature">
              <div className="rx-prev-footer-signature-line">
                <p className="rx-prev-footer-signature-label">Firma del Médico</p>
              </div>
            </div>
          </div>

          <p className="rx-prev-footer-disclaimer">
            Esta receta es válida únicamente con firma y sello del médico.
          </p>
        </footer>
      )}
    </div>
  );
});
