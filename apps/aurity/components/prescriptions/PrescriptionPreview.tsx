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
import {
  Prescription,
  FREQUENCY_LABELS,
  ROUTE_LABELS,
} from "@/lib/api/prescriptions";
import { PrescriptionStatusBadge } from "./PrescriptionStatusBadge";
import { Separator } from "@/components/ui/separator";

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
      className={`bg-white text-black p-8 max-w-[210mm] mx-auto font-serif ${className}`}
      style={{ minHeight: "297mm" }}
    >
      {/* Header / Membrete */}
      {showHeader && (
        <header className="text-center mb-6">
          {physician.institution && (
            <h1 className="text-lg font-bold uppercase tracking-wide">
              {physician.institution}
            </h1>
          )}
          <h2 className="text-base font-semibold mt-1">
            Dr(a). {physician.name}
          </h2>
          {physician.specialty && (
            <p className="text-sm text-gray-600">{physician.specialty}</p>
          )}
          <p className="text-sm mt-1">
            Cédula Profesional: {physician.professional_license}
          </p>
          {physician.specialty_license && (
            <p className="text-sm">
              Cédula de Especialidad: {physician.specialty_license}
            </p>
          )}
          {physician.address && (
            <p className="text-xs text-gray-500 mt-2">{physician.address}</p>
          )}
          {physician.phone && (
            <p className="text-xs text-gray-500">Tel: {physician.phone}</p>
          )}
        </header>
      )}

      <Separator className="my-4 bg-black" />

      {/* Title */}
      <div className="text-center mb-6">
        <h2 className="text-xl font-bold tracking-widest">RECETA MÉDICA</h2>
        <div className="flex justify-center mt-2">
          <PrescriptionStatusBadge status={prescription.status} size="sm" />
        </div>
      </div>

      {/* Patient Info */}
      <section className="mb-6 grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
        <div>
          <span className="font-semibold">Paciente:</span> {patient.name}
        </div>
        <div>
          <span className="font-semibold">Fecha:</span>{" "}
          {formatDate(prescription.created_at)}
        </div>
        {patient.age && (
          <div>
            <span className="font-semibold">Edad:</span> {patient.age}
          </div>
        )}
        {patient.weight_kg && (
          <div>
            <span className="font-semibold">Peso:</span> {patient.weight_kg} kg
          </div>
        )}
        {patient.allergies.length > 0 && (
          <div className="col-span-2 text-red-600">
            <span className="font-semibold">Alergias:</span>{" "}
            {patient.allergies.join(", ")}
          </div>
        )}
      </section>

      {/* Diagnosis */}
      <section className="mb-6">
        <h3 className="font-bold text-sm uppercase tracking-wide border-b border-gray-300 pb-1 mb-2">
          Diagnóstico
        </h3>
        <p className="text-sm">{diagnosis}</p>
        {prescription.diagnosis_code && (
          <p className="text-xs text-gray-500 mt-1">
            CIE-10: {prescription.diagnosis_code}
          </p>
        )}
      </section>

      <Separator className="my-4 border-dashed" />

      {/* Medications */}
      <section className="mb-6">
        <h3 className="font-bold text-sm uppercase tracking-wide border-b border-gray-300 pb-1 mb-4">
          Medicamentos
        </h3>
        <div className="space-y-4">
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
              <div key={index} className="text-sm pl-4 border-l-2 border-blue-500">
                <p className="font-semibold">
                  {index + 1}. Rx: {med.name}
                  {med.active_ingredient &&
                    med.active_ingredient !== med.name &&
                    ` (${med.active_ingredient})`}
                </p>
                <p className="ml-4">
                  {med.dosage} - {med.dosage_form}
                </p>
                <p className="ml-4">
                  {routeLabel}, {frequencyLabel}
                </p>
                <p className="ml-4">Duración: {durationLabel}</p>
                {med.quantity && (
                  <p className="ml-4 font-medium">Cantidad: {med.quantity}</p>
                )}
                {med.instructions && (
                  <p className="ml-4 italic text-gray-600">
                    Indicaciones: {med.instructions}
                  </p>
                )}
                {med.warnings && (
                  <p className="ml-4 text-amber-700 text-xs">
                    ⚠️ {med.warnings}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* General Instructions */}
      {prescription.general_instructions && (
        <section className="mb-6">
          <h3 className="font-bold text-sm uppercase tracking-wide border-b border-gray-300 pb-1 mb-2">
            Indicaciones Generales
          </h3>
          <p className="text-sm whitespace-pre-line">
            {prescription.general_instructions}
          </p>
        </section>
      )}

      {/* Next Appointment */}
      {prescription.next_appointment && (
        <section className="mb-6">
          <p className="text-sm">
            <span className="font-semibold">Próxima cita:</span>{" "}
            {prescription.next_appointment}
          </p>
        </section>
      )}

      {/* Footer */}
      {showFooter && (
        <footer className="mt-auto pt-12">
          <Separator className="mb-6" />

          <div className="flex justify-between items-end">
            <div className="text-xs text-gray-500">
              {prescription.signature_hash && (
                <p>Verificación: {prescription.signature_hash.slice(0, 16)}...</p>
              )}
              <p>
                Válida por {prescription.validity_days} días a partir de la
                fecha de emisión
              </p>
            </div>

            <div className="text-center">
              <div className="w-48 border-t border-black pt-2">
                <p className="text-sm font-medium">Firma del Médico</p>
              </div>
            </div>
          </div>

          <p className="text-xs text-gray-400 text-center mt-8">
            Esta receta es válida únicamente con firma y sello del médico.
          </p>
        </footer>
      )}
    </div>
  );
});
