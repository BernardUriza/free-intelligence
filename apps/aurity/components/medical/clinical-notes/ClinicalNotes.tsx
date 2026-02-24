'use client';

/**
 * ClinicalNotes - Professional SOAP Notes Editor
 *
 * Composition root that wires the useClinicalNotesForm hook
 * to section components. All state lives in the hook; each
 * SOAP section is a separate, independently testable component.
 *
 * SOLID principles applied:
 *  - SRP: state in hook, persistence in useSaveSOAP, UI in sections
 *  - OCP: new sections can be added without modifying existing ones
 *  - ISP: each section receives only the props (Pick<Handlers>) it needs
 *  - DIP: depends on handler interfaces, not implementation details
 *
 * @refactored 2026-02-22
 */

import type { ClinicalNotesProps } from './types';
import { POLLING_CONFIG } from './constants';
import { useClinicalNotesForm } from './hooks';
import { LoadingState, ErrorState } from './components';
import { PreviewModal, AIChatbot } from './modals';
import {
  ClinicalNotesToolbar,
  SubjectiveSection,
  ObjectiveSection,
  AssessmentSection,
  PlanSection,
  ActionBar,
  AISidebar,
} from './sections';

export function ClinicalNotes({
  sessionId,
  onNext,
  onPrevious,
  className = '',
}: ClinicalNotesProps) {
  const { state, handlers, aiSuggestions } = useClinicalNotesForm({
    sessionId,
    onNext,
    onPrevious,
    className,
  });

  // --- Loading / Error gates ---
  if (state.isLoading) {
    return (
      <div className={className}>
        <LoadingState
          status={state.pollingStatus}
          attempts={state.pollingAttempts}
          maxAttempts={POLLING_CONFIG.maxAttempts}
        />
      </div>
    );
  }

  if (state.error) {
    return (
      <div className={className}>
        <ErrorState message={state.error} />
      </div>
    );
  }

  // --- Main layout ---
  return (
    <div className={`cnotes-layout ${className}`}>
      <div className="cnotes-main">
        <ClinicalNotesToolbar
          sectionOrder={state.sectionOrder}
          showChatbot={state.showChatbot}
          showAIPanel={state.showAIPanel}
          handlers={handlers}
        />

        <SubjectiveSection
          soapData={state.soapData}
          newAllergy={state.newAllergy}
          voiceActive={state.voiceActive}
          handlers={handlers}
        />

        <ObjectiveSection soapData={state.soapData} handlers={handlers} />

        <AssessmentSection
          soapData={state.soapData}
          icd10Search={state.icd10Search}
          showICD10Dropdown={state.showICD10Dropdown}
          handlers={handlers}
        />

        <PlanSection
          soapData={state.soapData}
          newMedication={state.newMedication}
          showChatbot={state.showChatbot}
          handlers={handlers}
        />

        <ActionBar
          isComplete={state.isComplete}
          isSaving={state.isSaving}
          isSaved={state.isSaved}
          saveMessage={state.saveMessage}
          onPrevious={onPrevious}
          onNext={onNext}
          onSave={handlers.handleSave}
        />
      </div>

      {state.showAIPanel && <AISidebar suggestions={aiSuggestions} />}

      <PreviewModal
        isOpen={state.showPreviewModal}
        onClose={() => handlers.setShowPreviewModal(false)}
        soapData={state.soapData}
      />
      <AIChatbot
        isOpen={state.showChatbot}
        onClose={() => handlers.setShowChatbot(() => false)}
        sessionId={sessionId}
        soapData={state.soapData}
        onSOAPUpdate={handlers.setSOAPData}
      />
    </div>
  );
}
