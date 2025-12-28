/**
 * Medical Workflow Steps Configuration
 *
 * Defines the 6-step medical consultation workflow for AURITY
 */

import {
  Mic,
  MessageSquare,
  FileText,
  Shield,
  ClipboardList,
  Download,
} from 'lucide-react';
import {
  ConversationCapture,
  DialogueFlow,
  ClinicalNotes,
  EvidencePackViewer,
  OrderEntry,
  SummaryExport,
} from '@/components/medical';
import { WorkflowStep } from '@aurity-standalone/types/medical';

export interface MedicalWorkflowStepConfig {
  id: WorkflowStep;
  label: string;
  icon: any;
  component: any;
  color: string;
}

export const MedicalWorkflowSteps: MedicalWorkflowStepConfig[] = [
  {
    id: 'escuchar',
    label: 'Escuchar',
    icon: Mic,
    component: ConversationCapture,
    color: 'emerald',
  },
  {
    id: 'revisar',
    label: 'Revisar',
    icon: MessageSquare,
    component: DialogueFlow,
    color: 'cyan',
  },
  {
    id: 'notas',
    label: 'Notas SOAP',
    icon: FileText,
    component: ClinicalNotes,
    color: 'purple',
  },
  {
    id: 'evidencia',
    label: 'Evidencia',
    icon: Shield,
    component: EvidencePackViewer,
    color: 'indigo',
  },
  {
    id: 'ordenes',
    label: 'Órdenes',
    icon: ClipboardList,
    component: OrderEntry,
    color: 'amber',
  },
  {
    id: 'resumen',
    label: 'Finalizar',
    icon: Download,
    component: SummaryExport,
    color: 'rose',
  },
];
