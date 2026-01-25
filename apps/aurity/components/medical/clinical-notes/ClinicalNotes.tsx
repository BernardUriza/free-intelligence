'use client';

/**
 * ClinicalNotes - Professional SOAP Notes Editor
 *
 * Refactored 2025-12 into modular structure.
 */

import { useState, useCallback, useMemo, type ChangeEvent, type KeyboardEvent } from 'react';
import {
  Save,
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Eye,
  ArrowUpDown,
  Mic,
  MicOff,
  Sparkles,
  Search,
  Pill,
  Activity,
  Thermometer,
  Heart,
  Wind,
  TrendingUp,
  Plus,
  X,
  Brain,
  BookOpen,
  Zap,
  Edit3,
  MessageSquare,
  BarChart3,
  ClipboardList,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { medicalWorkflowApi } from '@aurity-standalone/api-client/medical-workflow';

// Local imports
import type { ClinicalNotesProps, SOAPData, VitalSigns, Medication, Diagnosis } from './types';
import { INITIAL_SOAP_DATA, NORMAL_VITAL_SIGNS, COMMON_ICD10, COMMON_DIAGNOSTIC_TESTS, POLLING_CONFIG } from './constants';
import { getSeverityStyles } from './utils';
import {
  SectionHeader,
  VitalSignInput,
  TagList,
  MedicationList,
  AISuggestionCard,
  LoadingState,
  ErrorState,
} from './components';
import { useAISuggestions, useSOAPPolling } from './hooks';
import { PreviewModal, AIChatbot } from './modals';

export function ClinicalNotes({
  sessionId,
  onNext,
  onPrevious,
  className = '',
}: ClinicalNotesProps) {
  // State
  const [soapData, setSOAPData] = useState<SOAPData>(INITIAL_SOAP_DATA);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // UI State
  const [showAIPanel, setShowAIPanel] = useState(true);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [showChatbot, setShowChatbot] = useState(false);
  const [sectionOrder, setSectionOrder] = useState<'SOAP' | 'APSO'>('SOAP');
  const [voiceActive, setVoiceActive] = useState<string | null>(null);

  // Search State
  const [icd10Search, setICD10Search] = useState('');
  const [showICD10Dropdown, setShowICD10Dropdown] = useState(false);
  const [newAllergy, setNewAllergy] = useState('');
  const [newMedication, setNewMedication] = useState<Medication>({ name: '', dose: '', frequency: '' });

  // Custom Hooks
  const aiSuggestions = useAISuggestions(soapData);

  const handleSOAPSuccess = useCallback((data: SOAPData) => {
    setSOAPData(data);
    setError(null);
  }, []);

  const handleSOAPError = useCallback((errorMessage: string) => {
    setError(errorMessage);
  }, []);

  const { isLoading, status, attempts } = useSOAPPolling(sessionId, handleSOAPSuccess, handleSOAPError);

  // Computed
  const filteredICD10 = useMemo(() => {
    if (!icd10Search.trim()) return [];
    const search = icd10Search.toLowerCase();
    return COMMON_ICD10.filter(
      (d) => d.code.toLowerCase().includes(search) || d.description.toLowerCase().includes(search)
    );
  }, [icd10Search]);

  const isComplete = soapData.chiefComplaint.trim().length > 0 && soapData.primaryDiagnosis !== null;

  // Handlers
  const updateField = useCallback(<K extends keyof SOAPData>(field: K, value: SOAPData[K]) => {
    setSOAPData((prev) => ({ ...prev, [field]: value }));
    setIsSaved(false);
  }, []);

  const updateVitalSign = useCallback((sign: keyof VitalSigns, value: string) => {
    setSOAPData((prev) => ({ ...prev, vitalSigns: { ...prev.vitalSigns, [sign]: value } }));
    setIsSaved(false);
  }, []);

  const addAllergy = useCallback(() => {
    const trimmed = newAllergy.trim();
    if (!trimmed) return;
    setSOAPData((prev) => ({ ...prev, allergies: [...prev.allergies, trimmed] }));
    setNewAllergy('');
  }, [newAllergy]);

  const removeAllergy = useCallback((index: number) => {
    setSOAPData((prev) => ({ ...prev, allergies: prev.allergies.filter((_, i) => i !== index) }));
  }, []);

  const addMedication = useCallback(() => {
    if (!newMedication.name.trim()) return;
    setSOAPData((prev) => ({ ...prev, medications: [...prev.medications, { ...newMedication }] }));
    setNewMedication({ name: '', dose: '', frequency: '' });
  }, [newMedication]);

  const removeMedication = useCallback((index: number) => {
    setSOAPData((prev) => ({ ...prev, medications: prev.medications.filter((_, i) => i !== index) }));
  }, []);

  const selectDiagnosis = useCallback((diagnosis: Diagnosis) => {
    setSOAPData((prev) => ({ ...prev, primaryDiagnosis: diagnosis }));
    setICD10Search('');
    setShowICD10Dropdown(false);
  }, []);

  const clearPrimaryDiagnosis = useCallback(() => {
    setSOAPData((prev) => ({ ...prev, primaryDiagnosis: null }));
  }, []);

  const toggleDiagnosticTest = useCallback((test: string) => {
    setSOAPData((prev) => ({
      ...prev,
      diagnosticTests: prev.diagnosticTests.includes(test)
        ? prev.diagnosticTests.filter((t) => t !== test)
        : [...prev.diagnosticTests, test],
    }));
  }, []);

  const removeDiagnosticTest = useCallback((index: number) => {
    setSOAPData((prev) => ({ ...prev, diagnosticTests: prev.diagnosticTests.filter((_, i) => i !== index) }));
  }, []);

  const removeDifferentialDiagnosis = useCallback((index: number) => {
    setSOAPData((prev) => ({ ...prev, differentialDiagnoses: prev.differentialDiagnoses.filter((_, i) => i !== index) }));
  }, []);

  const fillNormalVitals = useCallback(() => {
    setSOAPData((prev) => ({ ...prev, vitalSigns: NORMAL_VITAL_SIGNS }));
  }, []);

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    setIsSaved(false);
    setSaveMessage(null);

    try {
      const backendSOAP = {
        subjective: {
          chiefComplaint: soapData.chiefComplaint,
          hpi: soapData.hpi,
          pastMedicalHistory: soapData.currentMedications,
          allergies: soapData.allergies,
        },
        objective: {
          vitalSigns: Object.entries(soapData.vitalSigns)
            .filter(([, v]) => v)
            .map(([k, v]) => `${k}: ${v}`)
            .join(', '),
          physicalExam: soapData.physicalExam,
        },
        assessment: {
          primaryDiagnosis: soapData.primaryDiagnosis?.description || '',
          differentialDiagnoses: soapData.differentialDiagnoses.map((d) => d.description),
        },
        plan: {
          medications: soapData.medications,
          studies: soapData.diagnosticTests,
          followUp: soapData.followUp,
          treatment: '',
        },
      };

      const result = await medicalWorkflowApi.updateSOAP(sessionId, backendSOAP);

      setIsSaved(true);
      setSaveMessage({
        type: 'success',
        text: result.orders_created > 0
          ? `Notas guardadas. ${result.orders_created} órdenes médicas creadas automáticamente.`
          : 'Notas guardadas correctamente.',
      });

      setTimeout(() => setSaveMessage(null), 5000);
    } catch (err) {
      setSaveMessage({ type: 'error', text: err instanceof Error ? err.message : 'Error al guardar' });
      setIsSaved(false);
    } finally {
      setIsSaving(false);
    }
  }, [sessionId, soapData]);

  const handleKeyPress = useCallback((e: KeyboardEvent<HTMLInputElement>, action: () => void) => {
    if (e.key === 'Enter') action();
  }, []);

  // Render
  if (isLoading) {
    return (
      <div className={className}>
        <LoadingState status={status} attempts={attempts} maxAttempts={POLLING_CONFIG.maxAttempts} />
      </div>
    );
  }

  if (error) {
    return (
      <div className={className}>
        <ErrorState message={error} />
      </div>
    );
  }

  return (
    <div className={`grid grid-cols-12 gap-6 ${className}`}>
      {/* Main Content */}
      <div className="col-span-9 space-y-6">
        {/* Toolbar */}
        <div className="fi-flex-between bg-slate-800 p-4 rounded-lg border border-slate-700">
          <div>
            <h2 className="fi-title-2xl">Notas Clínicas SOAP</h2>
            <p className="fi-subtitle">Inputs estructurados con asistencia de IA</p>
          </div>
          <div className="flex gap-2">
            <Button onClick={() => setShowPreviewModal(true)} variant="secondary" icon={Eye}>Vista Previa</Button>
            <Button onClick={() => setSectionOrder((prev) => (prev === 'SOAP' ? 'APSO' : 'SOAP'))} variant="secondary" icon={ArrowUpDown}>{sectionOrder}</Button>
            <Button onClick={() => setShowChatbot((prev) => !prev)} variant={showChatbot ? 'success' : 'secondary'} icon={Zap}>Asistente IA</Button>
            <Button onClick={() => setShowAIPanel((prev) => !prev)} variant={showAIPanel ? 'purple' : 'secondary'} icon={Brain}>Sugerencias</Button>
          </div>
        </div>

        {/* Subjective Section */}
        <section className="fi-card-xl" aria-labelledby="subjective-heading">
          <SectionHeader icon={MessageSquare} title="Subjetivo" iconColor="text-blue-400" />
          <h4 id="subjective-heading" className="sr-only">Sección Subjetivo</h4>

          <div className="mb-4">
            <label htmlFor="chief-complaint" className="fi-label">Motivo de Consulta *</label>
            <div className="flex gap-2">
              <Input
                id="chief-complaint"
                type="text"
                value={soapData.chiefComplaint}
                onChange={(e: ChangeEvent<HTMLInputElement>) => updateField('chiefComplaint', e.target.value)}
                placeholder="Ej: Dolor de garganta por 3 días"
                className="flex-1"
              />
              <Button
                onClick={() => setVoiceActive((prev) => (prev === 'chief' ? null : 'chief'))}
                variant={voiceActive === 'chief' ? 'danger' : 'secondary'}
                icon={voiceActive === 'chief' ? MicOff : Mic}
                aria-label={voiceActive === 'chief' ? 'Desactivar dictado' : 'Activar dictado'}
              />
            </div>
          </div>

          <div className="mb-4">
            <label htmlFor="hpi" className="fi-label">Historia de Enfermedad Actual</label>
            <textarea
              id="hpi"
              value={soapData.hpi}
              onChange={(e) => updateField('hpi', e.target.value)}
              rows={3}
              placeholder="Descripción detallada de síntomas..."
              className="fi-textarea-blue"
            />
          </div>

          <div className="mb-4">
            <label className="fi-label">Alergias</label>
            <TagList items={soapData.allergies} onRemove={removeAllergy} />
            <div className="flex gap-2">
              <Input
                type="text"
                value={newAllergy}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setNewAllergy(e.target.value)}
                onKeyPress={(e: KeyboardEvent<HTMLInputElement>) => handleKeyPress(e, addAllergy)}
                placeholder="Agregar alergia..."
                className="flex-1"
              />
              <Button onClick={addAllergy} variant="primary" icon={Plus} />
            </div>
          </div>

          <div>
            <label className="fi-label">Medicamentos Actuales</label>
            {soapData.currentMedications.length > 0 && (
              <div className="space-y-2 mb-2">
                {soapData.currentMedications.map((med, idx) => (
                  <div key={`current-med-${idx}`} className="flex items-center gap-2 bg-slate-900 p-3 rounded-lg border border-slate-600">
                    <Pill className="h-4 w-4 fi-text-primary" aria-hidden="true" />
                    <span className="text-white flex-1">{med}</span>
                    <Button variant="ghost" size="sm" icon={X} className="text-slate-400 hover:text-red-400" aria-label={`Eliminar ${med}`} />
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Objective Section */}
        <section className="fi-card-xl" aria-labelledby="objective-heading">
          <SectionHeader icon={BarChart3} title="Objetivo" iconColor="text-cyan-400" />
          <h4 id="objective-heading" className="sr-only">Sección Objetivo</h4>

          <div className="mb-4">
            <div className="fi-flex-between mb-3">
              <span className="text-sm font-medium fi-text">Signos Vitales</span>
              <Button onClick={fillNormalVitals} variant="ghost" size="sm" icon={CheckCircle2} className="bg-emerald-600/20 hover:bg-emerald-600/30 fi-text-success">
                Llenar valores normales
              </Button>
            </div>

            <div className="grid grid-cols-5 gap-3">
              <VitalSignInput icon={Thermometer} iconColor="text-red-400" label="Temp." value={soapData.vitalSigns.temperature} onChange={(v) => updateVitalSign('temperature', v)} placeholder="36.5" unit="°C" step="0.1" />
              <VitalSignInput icon={Heart} iconColor="text-red-400" label="FC" value={soapData.vitalSigns.heartRate} onChange={(v) => updateVitalSign('heartRate', v)} placeholder="72" unit="bpm" inputWidth="w-12" />
              <VitalSignInput icon={Activity} iconColor="fi-text-primary" label="PA" value={soapData.vitalSigns.bloodPressure} onChange={(v) => updateVitalSign('bloodPressure', v)} placeholder="120/80" type="text" inputWidth="w-16" />
              <VitalSignInput icon={Wind} iconColor="text-cyan-400" label="FR" value={soapData.vitalSigns.respiratoryRate} onChange={(v) => updateVitalSign('respiratoryRate', v)} placeholder="16" unit="/min" inputWidth="w-12" />
              <VitalSignInput icon={TrendingUp} iconColor="fi-text-green" label="SpO₂" value={soapData.vitalSigns.oxygenSaturation} onChange={(v) => updateVitalSign('oxygenSaturation', v)} placeholder="98" unit="%" inputWidth="w-12" />
            </div>
          </div>

          <div>
            <label htmlFor="physical-exam" className="block fi-label flex items-center gap-2">
              <Edit3 className="h-4 w-4 text-cyan-400" aria-hidden="true" />
              Examen Físico
            </label>
            <textarea id="physical-exam" value={soapData.physicalExam} onChange={(e) => updateField('physicalExam', e.target.value)} rows={3} placeholder="Descripción del examen físico..." className="fi-textarea-cyan" />
          </div>
        </section>

        {/* Assessment Section */}
        <section className="fi-card-xl" aria-labelledby="assessment-heading">
          <SectionHeader icon={Search} title="Evaluación" iconColor="text-purple-400" />
          <h4 id="assessment-heading" className="sr-only">Sección Evaluación</h4>

          <div className="mb-4">
            <label htmlFor="icd10-search" className="fi-label">Diagnóstico Principal</label>
            <div className="relative">
              <Input
                id="icd10-search"
                type="text"
                value={icd10Search}
                onChange={(e: ChangeEvent<HTMLInputElement>) => { setICD10Search(e.target.value); setShowICD10Dropdown(true); }}
                onFocus={() => setShowICD10Dropdown(true)}
                icon={Search}
                placeholder="Buscar diagnóstico por código ICD-10 o nombre..."
              />

              {showICD10Dropdown && filteredICD10.length > 0 && (
                <div className="fi-dropdown" role="listbox">
                  {filteredICD10.map((diagnosis) => (
                    <button key={diagnosis.code} type="button" onClick={() => selectDiagnosis(diagnosis)} className="w-full p-3 hover:bg-slate-800 text-left fi-border-bottom last:border-none" role="option" aria-selected={false}>
                      <div className="fi-flex-between">
                        <div>
                          <span className="text-white font-medium">{diagnosis.code}</span>
                          <span className="text-slate-400 text-sm ml-2">{diagnosis.description}</span>
                        </div>
                        <span className={`text-xs px-2 py-1 rounded ${getSeverityStyles(diagnosis.severity)}`}>{diagnosis.severity}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {soapData.primaryDiagnosis && (
              <div className="mt-3 bg-purple-500/10 border border-purple-500/30 rounded-lg p-3">
                <div className="fi-flex-between">
                  <div>
                    <span className="fi-text-purple font-semibold">{soapData.primaryDiagnosis.code}</span>
                    <span className="text-white ml-2">{soapData.primaryDiagnosis.description}</span>
                  </div>
                  <Button onClick={clearPrimaryDiagnosis} variant="ghost" size="sm" icon={X} className="text-slate-400 hover:text-red-400" aria-label="Eliminar diagnóstico principal" />
                </div>
              </div>
            )}
          </div>

          {soapData.differentialDiagnoses.length > 0 && (
            <div className="mt-4">
              <span className="fi-label">Diagnósticos Diferenciales</span>
              <div className="space-y-2">
                {soapData.differentialDiagnoses.map((diff, idx) => (
                  <div key={`diff-${idx}`} className="bg-purple-500/5 border border-purple-500/20 rounded-lg p-3">
                    <div className="fi-flex-between">
                      <div>
                        {diff.code && <span className="fi-text-purple font-semibold mr-2">{diff.code}</span>}
                        <span className="text-white">{diff.description}</span>
                      </div>
                      <Button onClick={() => removeDifferentialDiagnosis(idx)} variant="ghost" size="sm" icon={X} className="text-slate-400 hover:text-red-400" aria-label={`Eliminar ${diff.description}`} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Plan Section */}
        <section className="fi-card-xl" aria-labelledby="plan-heading">
          <SectionHeader icon={ClipboardList} title="Plan" iconColor="text-emerald-400" action={<Button onClick={() => setShowChatbot((prev) => !prev)} variant={showChatbot ? 'success' : 'secondary'} size="sm" icon={Zap}>Asistente IA</Button>} />
          <h4 id="plan-heading" className="sr-only">Sección Plan</h4>

          <div className="mb-4">
            <span className="fi-label">Tratamiento Farmacológico</span>
            <MedicationList medications={soapData.medications} onRemove={removeMedication} />
            <div className="grid grid-cols-3 gap-3 mb-2">
              <Input type="text" value={newMedication.name} onChange={(e: ChangeEvent<HTMLInputElement>) => setNewMedication((prev) => ({ ...prev, name: e.target.value }))} placeholder="Medicamento" />
              <Input type="text" value={newMedication.dose} onChange={(e: ChangeEvent<HTMLInputElement>) => setNewMedication((prev) => ({ ...prev, dose: e.target.value }))} placeholder="Dosis" />
              <Input type="text" value={newMedication.frequency} onChange={(e: ChangeEvent<HTMLInputElement>) => setNewMedication((prev) => ({ ...prev, frequency: e.target.value }))} placeholder="Frecuencia" />
            </div>
            <Button onClick={addMedication} variant="primary" icon={Plus} size="sm">Agregar medicamento</Button>
          </div>

          <div className="mb-4">
            <span className="fi-label">Estudios de Laboratorio / Gabinete</span>
            <div className="space-y-2">
              {COMMON_DIAGNOSTIC_TESTS.map((test) => (
                <label key={test} className="flex items-center gap-2 bg-slate-900 p-3 rounded-lg border border-slate-600 cursor-pointer hover:bg-slate-800">
                  <input type="checkbox" checked={soapData.diagnosticTests.includes(test)} onChange={() => toggleDiagnosticTest(test)} className="rounded" />
                  <span className="text-white">{test}</span>
                </label>
              ))}
            </div>

            {soapData.diagnosticTests.length > 0 && (
              <div className="mt-4">
                <span className="text-sm font-medium text-slate-400 mb-2 block">Órdenes Seleccionadas:</span>
                <div className="space-y-2">
                  {soapData.diagnosticTests.map((test, idx) => (
                    <div key={`selected-test-${idx}`} className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3">
                      <div className="fi-flex-between">
                        <span className="text-white">{test}</span>
                        <Button onClick={() => removeDiagnosticTest(idx)} variant="ghost" size="sm" icon={X} className="text-slate-400 hover:text-red-400" aria-label={`Eliminar ${test}`} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div>
            <label htmlFor="follow-up" className="fi-label">Seguimiento</label>
            <textarea id="follow-up" value={soapData.followUp} onChange={(e) => updateField('followUp', e.target.value)} rows={2} placeholder="Instrucciones de seguimiento..." className="fi-textarea-blue" />
          </div>
        </section>

        {/* Action Buttons */}
        <div className="flex gap-4">
          {onPrevious && <Button onClick={onPrevious} variant="secondary" size="lg" className="flex-1">Anterior</Button>}
          <Button onClick={handleSave} disabled={!isComplete || isSaving} variant={isComplete ? 'primary' : 'secondary'} size="lg" icon={isSaving ? undefined : isSaved ? CheckCircle2 : Save} loading={isSaving} className="flex-1">
            {isSaving ? 'Guardando...' : isSaved ? 'Guardado' : 'Guardar Notas'}
          </Button>
          {onNext && <Button onClick={onNext} disabled={!isComplete} variant={isComplete ? 'primary' : 'secondary'} size="lg" icon={ChevronRight} className="flex-1">Continuar</Button>}
        </div>

        {saveMessage && (
          <div className={`mt-4 p-4 rounded-lg flex items-center gap-3 ${saveMessage.type === 'success' ? 'bg-emerald-500/10 border border-emerald-500/30' : 'bg-red-500/10 border border-red-500/30'}`} role="alert">
            {saveMessage.type === 'success' ? <CheckCircle2 className="h-5 w-5 fi-text-success" aria-hidden="true" /> : <AlertCircle className="h-5 w-5 text-red-400" aria-hidden="true" />}
            <p className={`text-sm ${saveMessage.type === 'success' ? 'fi-text-success' : 'text-red-400'}`}>{saveMessage.text}</p>
          </div>
        )}
      </div>

      {/* AI Suggestions Panel */}
      {showAIPanel && (
        <aside className="col-span-3" aria-label="Panel de sugerencias de IA">
          <div className="bg-gradient-to-br from-purple-900/50 to-blue-900/50 rounded-xl p-4 border border-purple-500/30 sticky top-6">
            <div className="fi-flex-gap mb-4">
              <Sparkles className="h-5 w-5 fi-text-purple" aria-hidden="true" />
              <h3 className="text-lg font-bold text-white">Asistente IA</h3>
            </div>

            {aiSuggestions.length === 0 ? (
              <p className="text-slate-400 text-sm">Completa los campos para recibir sugerencias...</p>
            ) : (
              <div className="space-y-3">
                {aiSuggestions.map((suggestion, idx) => (
                  <AISuggestionCard key={idx} suggestion={suggestion} />
                ))}
              </div>
            )}

            <div className="mt-4 pt-4 fi-border-top">
              <p className="fi-text-xs mb-2">Acciones Rápidas</p>
              <div className="space-y-2">
                <Button variant="ghost" size="sm" icon={Sparkles} fullWidth className="justify-start bg-slate-800 hover:bg-slate-700">Generar resumen</Button>
                <Button variant="ghost" size="sm" icon={BookOpen} fullWidth className="justify-start bg-slate-800 hover:bg-slate-700">Buscar guías clínicas</Button>
              </div>
            </div>
          </div>
        </aside>
      )}

      {/* Modals */}
      <PreviewModal isOpen={showPreviewModal} onClose={() => setShowPreviewModal(false)} soapData={soapData} />
      <AIChatbot isOpen={showChatbot} onClose={() => setShowChatbot(false)} sessionId={sessionId} soapData={soapData} onSOAPUpdate={setSOAPData} />
    </div>
  );
}
