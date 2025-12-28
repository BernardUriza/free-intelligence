"use client";

/**
 * HDF5 Preview Component - Phase 5 (FI-ONBOARD-006)
 *
 * Real-time JSON preview of how patient data will be structured in HDF5
 */

import { PatientFormData } from "./PatientSetupForm";

interface HDF5PreviewProps {
  patientData: PatientFormData;
}

export function HDF5Preview({ patientData }: HDF5PreviewProps) {
  // Generate session_id format
  const now = new Date();
  const sessionId = `session_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`;

  // Build HDF5 structure
  const hdf5Structure = {
    sessions: {
      [sessionId]: {
        metadata: {
          patient: {
            nombre: patientData.nombre || "<nombre_paciente>",
            edad: patientData.edad || "<edad>",
            genero: patientData.genero || "<genero>",
            ...(patientData.motivoConsulta && { motivo_consulta: patientData.motivoConsulta }),
          },
          session_id: sessionId,
          created_at: now.toISOString(),
          status: "PENDING",
        },
        tasks: {
          TRANSCRIPTION: {
            chunks: [],
            metadata: {
              status: "pending",
              progress: 0,
            },
          },
          DIARIZATION: {
            chunks: [],
            metadata: {
              status: "pending",
            },
          },
          SOAP_GENERATION: {
            chunks: [],
            metadata: {
              status: "pending",
              completeness: 0,
            },
          },
          ENCRYPTION: {
            metadata: {
              status: "pending",
              algorithm: "AES-GCM-256",
            },
          },
        },
      },
    },
  };

  /**
   * Syntax highlight JSON
   */
  const syntaxHighlight = (json: any): JSX.Element => {
    const jsonString = JSON.stringify(json, null, 2);

    const highlighted = jsonString
      .replace(/(".*?"):/g, '<span class="fi-text-info">$1</span>:')
      .replace(/: (".*?")/g, ': <span class="fi-text-success">$1</span>')
      .replace(/: (\d+)/g, ': <span class="fi-text-purple">$1</span>')
      .replace(/: (true|false|null)/g, ': <span class="text-yellow-400">$1</span>')
      .replace(/(&lt;.*?&gt;)/g, '<span class="fi-text-error italic">$1</span>');

    return <div dangerouslySetInnerHTML={{ __html: highlighted }} />;
  };

  const isDataComplete = !!(
    patientData.nombre &&
    patientData.edad !== '' &&
    patientData.genero
  );

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="fi-flex-between">
        <h3 className="text-lg font-semibold text-slate-200">
          📊 Preview: HDF5 Structure
        </h3>
        {isDataComplete && (
          <span className="flex items-center gap-2 text-xs fi-text-success bg-emerald-950/30 px-3 py-1 rounded-full">
            <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
            Live Update
          </span>
        )}
      </div>

      {/* Explanation */}
      <div className="p-4 bg-blue-950/20 border border-blue-700/30 rounded-xl">
        <p className="text-xs text-blue-300">
          <strong>💡 Tip:</strong> Cada vez que cambies los datos del paciente, verás cómo se estructura
          en tiempo real dentro del archivo HDF5 (<code className="fi-text-info">/storage/corpus.h5</code>).
        </p>
      </div>

      {/* JSON Preview */}
      <div className="bg-slate-950/70 border border-slate-700/50 rounded-xl p-4 overflow-x-auto">
        <pre className="text-xs font-mono leading-relaxed">
          {syntaxHighlight(hdf5Structure)}
        </pre>
      </div>

      {/* Session ID Explanation */}
      <div className="p-4 bg-slate-900/60 border border-slate-700/50 rounded-xl space-y-3">
        <div className="flex items-start gap-3">
          <span className="text-2xl">🔑</span>
          <div>
            <p className="text-sm font-semibold text-slate-200">Session ID Format</p>
            <p className="fi-text-xs mt-1">
              <code className="fi-text-success bg-slate-950/50 px-2 py-1 rounded">
                {sessionId}
              </code>
            </p>
            <p className="fi-text-xs mt-2">
              Formato: <strong>session_YYYYMMDD_HHMMSS</strong> · Timestamp único por consulta
            </p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <span className="text-2xl">📁</span>
          <div>
            <p className="text-sm font-semibold text-slate-200">Append-Only Storage</p>
            <p className="fi-text-xs mt-1">
              Cada sesión se escribe una sola vez. No hay modificaciones - solo nuevas sesiones.
              Esto garantiza <strong>inmutabilidad</strong> y auditoría completa.
            </p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <span className="text-2xl">🔐</span>
          <div>
            <p className="text-sm font-semibold text-slate-200">Task-Based Architecture</p>
            <p className="fi-text-xs mt-1">
              Cada sesión tiene 4 task types: <strong>TRANSCRIPTION</strong> → <strong>DIARIZATION</strong> → <strong>SOAP_GENERATION</strong> → <strong>ENCRYPTION</strong>
            </p>
          </div>
        </div>
      </div>

      {/* Data Completeness Indicator */}
      {!isDataComplete && (
        <div className="p-4 bg-yellow-950/20 border border-yellow-700/30 rounded-xl">
          <p className="text-xs text-yellow-300 flex items-center gap-2">
            <span>⏳</span>
            Completa los campos requeridos para ver la estructura completa
          </p>
        </div>
      )}
    </div>
  );
}
