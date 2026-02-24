/**
 * PreviewTab Component
 *
 * Prescription preview with action toolbar (save, sign, print).
 * Single Responsibility: preview display + action buttons.
 *
 * @author Bernard Uriza Orozco
 * @created 2025-12-28
 * @refactored 2026-02-22
 */

"use client";

import type { Prescription } from "@/lib/api/prescriptions";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PrescriptionPreview } from "../PrescriptionPreview";
import { PrescriptionStatusBadge } from "../PrescriptionStatusBadge";
import { Save, Signature, Printer, AlertCircle } from "lucide-react";

interface PreviewTabProps {
  previewPrescription: Prescription | null;
  createdPrescription: Prescription | null;
  isSubmitting: boolean;
  onSubmit: () => void;
  onSign: () => void;
  onPrint: () => void;
}

export function PreviewTab({
  previewPrescription,
  createdPrescription,
  isSubmitting,
  onSubmit,
  onSign,
  onPrint,
}: PreviewTabProps) {
  if (!previewPrescription) {
    return <EmptyPreview />;
  }

  return (
    <div className="rx-preview-stack">
      <PreviewToolbar
        prescription={previewPrescription}
        createdPrescription={createdPrescription}
        isSubmitting={isSubmitting}
        onSubmit={onSubmit}
        onSign={onSign}
        onPrint={onPrint}
      />
      <div className="rx-preview-frame">
        <PrescriptionPreview prescription={previewPrescription} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components (co-located — small and tightly coupled)
// ---------------------------------------------------------------------------

interface PreviewToolbarProps {
  prescription: Prescription;
  createdPrescription: Prescription | null;
  isSubmitting: boolean;
  onSubmit: () => void;
  onSign: () => void;
  onPrint: () => void;
}

function PreviewToolbar({
  prescription,
  createdPrescription,
  isSubmitting,
  onSubmit,
  onSign,
  onPrint,
}: PreviewToolbarProps) {
  const showSave = !createdPrescription;
  const showSign =
    createdPrescription !== null && createdPrescription.status === "draft";
  const showPrint = createdPrescription !== null;

  return (
    <div className="rx-preview-toolbar">
      <div className="rx-preview-status">
        <span className="rx-preview-status-label">Estado:</span>
        <PrescriptionStatusBadge status={prescription.status} />
      </div>
      <div className="rx-preview-actions">
        {showSave && (
          <Button onClick={onSubmit} disabled={isSubmitting} variant="primary">
            <Save className="rx-btn-icon" />
            Guardar Receta
          </Button>
        )}
        {showSign && (
          <Button onClick={onSign} disabled={isSubmitting} variant="primary">
            <Signature className="rx-btn-icon" />
            Firmar Receta
          </Button>
        )}
        {showPrint && (
          <Button
            onClick={onPrint}
            variant="outline"
            className="rx-print-hidden"
          >
            <Printer className="rx-btn-icon" />
            Imprimir
          </Button>
        )}
      </div>
    </div>
  );
}

function EmptyPreview() {
  return (
    <Card>
      <CardContent className="rx-empty-content">
        <AlertCircle className="rx-empty-icon" />
        <p>Complete la información para ver la vista previa</p>
        <p className="rx-empty-hint">
          Se requiere: paciente, médico, diagnóstico y al menos un medicamento
        </p>
      </CardContent>
    </Card>
  );
}
