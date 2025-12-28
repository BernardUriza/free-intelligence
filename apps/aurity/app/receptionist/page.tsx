"use client";

/**
 * Receptionist Page - AURITY Free Intelligence
 *
 * Renders the conversational check-in widget for clinic receptionists.
 * This page is designed to be opened in a separate window/tab.
 */

import { Suspense } from 'react';
import { ReceptionistChatWidget } from '@/components/checkin/ReceptionistChatWidget';
import { useSearchParams } from 'next/navigation';

function ReceptionistPageContent() {
  const searchParams = useSearchParams();
  const clinicId = searchParams.get('clinicId');
  const clinicName = searchParams.get('clinicName');
  const patientName = searchParams.get('patientName');

  if (!clinicId) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-slate-950 text-white">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-500">Error de Configuración</h1>
          <p className="mt-2 text-slate-400">
            Falta el parámetro `clinicId` en la URL.
          </p>
        </div>
      </div>
    );
  }

  return (
    <ReceptionistChatWidget
      clinicId={clinicId}
      clinicName={clinicName || undefined}
      patientName={patientName || undefined}
    />
  );
}

export default function ReceptionistPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ReceptionistPageContent />
    </Suspense>
  );
}
