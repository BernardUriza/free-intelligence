'use client';

import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { SOAPData } from '../types';

interface PreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  soapData: SOAPData;
}

export function PreviewModal({ isOpen, onClose, soapData }: PreviewModalProps) {
  if (!isOpen) return null;

  return (
    <div
      className="med-preview-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="preview-title"
    >
      <div className="med-preview-content">
        <div className="sticky top-0 bg-slate-900 fi-border-bottom p-6 flex justify-between items-center">
          <div>
            <h3 id="preview-title" className="fi-title-xl">
              Vista Previa - Notas SOAP
            </h3>
            <p className="fi-subtitle">Solo lectura</p>
          </div>
          <Button
            onClick={onClose}
            variant="secondary"
            icon={X}
            aria-label="Cerrar vista previa"
          />
        </div>

        <div className="p-6 space-y-6">
          {/* Subjective Preview */}
          <div>
            <h4 className="text-lg font-bold fi-text-success mb-2">
              Subjetivo
            </h4>
            <div className="space-y-2 fi-text">
              <p>
                <span className="font-semibold">Motivo de Consulta:</span>{' '}
                {soapData.chiefComplaint || 'N/A'}
              </p>
              <p>
                <span className="font-semibold">Historia:</span>
              </p>
              <p className="whitespace-pre-wrap">
                {soapData.hpi || 'N/A'}
              </p>
            </div>
          </div>

          {/* Objective Preview */}
          <div>
            <h4 className="text-lg font-bold text-cyan-400 mb-2">
              Objetivo
            </h4>
            <div className="space-y-2 fi-text">
              <p className="font-semibold">Signos Vitales:</p>
              <div className="grid grid-cols-2 gap-2 ml-4">
                <p>
                  Temperatura: {soapData.vitalSigns.temperature || 'N/A'} °C
                </p>
                <p>FC: {soapData.vitalSigns.heartRate || 'N/A'} bpm</p>
                <p>PA: {soapData.vitalSigns.bloodPressure || 'N/A'}</p>
                <p>
                  FR: {soapData.vitalSigns.respiratoryRate || 'N/A'} /min
                </p>
                <p>
                  SpO₂: {soapData.vitalSigns.oxygenSaturation || 'N/A'} %
                </p>
              </div>
              <p className="mt-2">
                <span className="font-semibold">Examen Físico:</span>
              </p>
              <p className="whitespace-pre-wrap">
                {soapData.physicalExam || 'N/A'}
              </p>
            </div>
          </div>

          {/* Assessment Preview */}
          <div>
            <h4 className="text-lg font-bold fi-text-purple mb-2">
              Evaluación
            </h4>
            <div className="space-y-2 fi-text">
              <p>
                <span className="font-semibold">Diagnóstico Principal:</span>{' '}
                {soapData.primaryDiagnosis?.description || 'N/A'}
              </p>
              {soapData.differentialDiagnoses.length > 0 && (
                <>
                  <p className="font-semibold mt-2">
                    Diagnósticos Diferenciales:
                  </p>
                  <ul className="list-disc ml-6">
                    {soapData.differentialDiagnoses.map((diff, idx) => (
                      <li key={idx}>{diff.description}</li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          </div>

          {/* Plan Preview */}
          <div>
            <h4 className="text-lg font-bold text-amber-400 mb-2">Plan</h4>
            <div className="space-y-2 fi-text">
              {soapData.medications.length > 0 && (
                <>
                  <p className="font-semibold">Medicamentos:</p>
                  <ul className="list-disc ml-6">
                    {soapData.medications.map((med, idx) => (
                      <li key={idx}>
                        {med.name} - {med.dose} - {med.frequency}
                      </li>
                    ))}
                  </ul>
                </>
              )}
              {soapData.diagnosticTests.length > 0 && (
                <>
                  <p className="font-semibold mt-2">
                    Estudios Solicitados:
                  </p>
                  <ul className="list-disc ml-6">
                    {soapData.diagnosticTests.map((test, idx) => (
                      <li key={idx}>{test}</li>
                    ))}
                  </ul>
                </>
              )}
              <p className="mt-2">
                <span className="font-semibold">Seguimiento:</span>
              </p>
              <p className="whitespace-pre-wrap">
                {soapData.followUp || 'N/A'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
