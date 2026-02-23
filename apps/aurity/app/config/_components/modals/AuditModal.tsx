/**
 * AuditModal
 *
 * Shows audit trail information: HDF5 log structure,
 * upcoming UI, and manual inspection instructions.
 */

import { Button } from '@/components/ui/button';
import type { ModalProps } from '../types';

const AUDIT_LOG_SAMPLE = `{
  "timestamp": "2025-11-20T02:45:12Z",
  "operation": "llm_generate",
  "user_id": "user-123...",
  "user_email": "doctor@hospital.com",
  "payload_hash": "sha256:abc...",
  "result_hash": "sha256:def...",
  "cost_usd": 0.0042,
  "level": "info"
}`;

const UPCOMING_FEATURES = [
  'Timeline de eventos con filtros',
  'Búsqueda por usuario, operación, fecha',
  'Export de logs (CSV, JSON)',
  'Alertas en tiempo real',
  'Estadísticas de uso por usuario',
] as const;

export function AuditModal({ onClose }: ModalProps) {
  return (
    <div className="fi-modal-backdrop" onClick={onClose}>
      <div className="cfg-modal-md" onClick={(e) => e.stopPropagation()}>
        <div className="cfg-modal-header">
          <h2 className="fi-title-xl">Audit Trail</h2>
          <p className="cfg-subtitle-gap">Registro de auditoría del sistema</p>
        </div>

        <div className="cfg-section-body">
          <ActiveAuditInfo />
          <LogStructure />
          <UpcomingUI />
          <ManualInspection />
        </div>

        <div className="cfg-modal-footer-single">
          <Button onClick={onClose} variant="secondary" size="sm">
            Cerrar
          </Button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Co-located sub-components
// ---------------------------------------------------------------------------

function ActiveAuditInfo() {
  return (
    <div className="cfg-info-card-emerald">
      <h3 className="cfg-info-title-emerald">Si Backend Audit Trail Activo</h3>
      <p className="cfg-info-text-body">
        El backend ya registra todas las operaciones en HDF5:
      </p>
      <ul className="cfg-list-bullets">
        <li>Operaciones LLM (generate, embed)</li>
        <li>Exportaciones de datos</li>
        <li>Búsquedas en corpus</li>
        <li>Operaciones críticas (delete)</li>
      </ul>
      <div className="cfg-code-wrap">
        <code className="cfg-code-text-success">
          Location: /storage/corpus.h5:/audit_logs
        </code>
      </div>
    </div>
  );
}

function LogStructure() {
  return (
    <div className="cfg-section-inner">
      <h3 className="cfg-title-gap">Estructura de Logs</h3>
      <div className="cfg-pre-wrap">
        <pre className="cfg-pre-text">{AUDIT_LOG_SAMPLE}</pre>
      </div>
    </div>
  );
}

function UpcomingUI() {
  return (
    <div className="cfg-info-card-yellow">
      <h3 className="cfg-info-title-yellow">UI de Auditoría - En Desarrollo</h3>
      <p className="cfg-info-text-yellow">
        Próximamente: Interfaz para visualizar y filtrar logs de auditoría
      </p>
      <ul className="cfg-list-bullets-tight">
        {UPCOMING_FEATURES.map((feature) => (
          <li key={feature}>{feature}</li>
        ))}
      </ul>
    </div>
  );
}

function ManualInspection() {
  return (
    <div className="cfg-info-card-blue">
      <h3 className="cfg-info-title-blue">Inspección Manual</h3>
      <p className="cfg-info-text-body-sm">
        Puedes inspeccionar los logs manualmente usando:
      </p>
      <div className="cfg-code-wrap-plain">
        <code className="cfg-code-text-primary">
          python backend/tools/inspect_corpus.py --audit-logs
        </code>
      </div>
    </div>
  );
}
