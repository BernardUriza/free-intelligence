/**
 * ClinicalNotesToolbar Component
 *
 * Top toolbar with action buttons: preview, section order, chatbot, AI panel.
 * SRP: toolbar UI only.
 *
 * @created 2026-02-22
 */

'use client';

import { Eye, ArrowUpDown, Zap, Brain } from 'lucide-react';
import { Button } from '@/components/ui/button';

import type { ClinicalNotesFormHandlers, SectionOrder } from '../types';

interface ClinicalNotesToolbarProps {
  sectionOrder: SectionOrder;
  showChatbot: boolean;
  showAIPanel: boolean;
  handlers: Pick<
    ClinicalNotesFormHandlers,
    | 'setShowPreviewModal'
    | 'setSectionOrder'
    | 'setShowChatbot'
    | 'setShowAIPanel'
  >;
}

export function ClinicalNotesToolbar({
  sectionOrder,
  showChatbot,
  showAIPanel,
  handlers,
}: ClinicalNotesToolbarProps) {
  return (
    <div className="cnotes-toolbar">
      <div>
        <h2 className="fi-title-2xl">Notas Clínicas SOAP</h2>
        <p className="fi-subtitle">
          Inputs estructurados con asistencia de IA
        </p>
      </div>
      <div className="cnotes-toolbar-actions">
        <Button
          onClick={() => handlers.setShowPreviewModal(true)}
          variant="secondary"
          icon={Eye}
        >
          Vista Previa
        </Button>
        <Button
          onClick={() =>
            handlers.setSectionOrder((prev) =>
              prev === 'SOAP' ? 'APSO' : 'SOAP',
            )
          }
          variant="secondary"
          icon={ArrowUpDown}
        >
          {sectionOrder}
        </Button>
        <Button
          onClick={() => handlers.setShowChatbot((prev) => !prev)}
          variant={showChatbot ? 'success' : 'secondary'}
          icon={Zap}
        >
          Asistente IA
        </Button>
        <Button
          onClick={() => handlers.setShowAIPanel((prev) => !prev)}
          variant={showAIPanel ? 'purple' : 'secondary'}
          icon={Brain}
        >
          Sugerencias
        </Button>
      </div>
    </div>
  );
}
