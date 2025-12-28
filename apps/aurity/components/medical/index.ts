/**
 * Medical Workflow Components - AURITY
 *
 * Complete medical workflow components integrated with FI backend.
 * All components use production endpoints (no demo/mock data).
 *
 * Workflow Steps:
 * 1. ConversationCapture - Audio recording + transcription
 * 2. DialogueFlow - Review + edit dialogue
 * 3. ClinicalNotes - SOAP notes editor
 * 4. OrderEntry - Medical orders management
 * 5. SummaryExport - Export to corpus/PDF/Markdown
 *
 * File: apps/aurity/components/medical/index.ts
 */

export { ConversationCapture } from './ConversationCapture';
export { DialogueFlow } from './DialogueFlow';
export { ClinicalNotes } from './clinical-notes';
export { EvidencePackViewer } from './EvidencePackViewer';
export { OrderEntry } from './order-entry';
export { SummaryExport } from './SummaryExport';
export { DiarizationProcessingModal } from './DiarizationProcessingModal';
export { PatientInfoModal, type PatientInfo } from './PatientInfoModal';
export { SessionAuditPanel } from './SessionAuditPanel';
export { WebSpeechStatusBadge } from './WebSpeechStatusBadge';
