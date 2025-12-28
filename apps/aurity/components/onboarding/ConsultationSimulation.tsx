"use client";

/**
 * Consultation Simulation Component - Phase 6 (FI-ONBOARD-007)
 *
 * Interactive medical consultation simulation with 3 modes:
 * 1. Auto-play: Watch the full flow (2 min)
 * 2. Guided: FI guides step-by-step (5 min)
 * 3. Hands-on: User executes each step (10 min)
 */

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { ProgressMonitor, TaskProgress } from "./ProgressMonitor";
import {
  SIMULATED_CHUNKS,
  SIMULATED_TRANSCRIPTIONS,
  SIMULATED_DIARIZATION,
  SIMULATED_SOAP,
  LATENCY,
  PROGRESS_MESSAGES,
  AudioChunkSimulation,
} from "@/lib/simulation-data";

type SimulationMode = 'select' | 'auto' | 'guided' | 'hands-on';
type SimulationStep =
  | 'intro'
  | 'upload'
  | 'checkpoint'
  | 'transcription'
  | 'diarization'
  | 'soap'
  | 'export'
  | 'complete';

interface ConsultationSimulationProps {
  onComplete: () => void;
}

export function ConsultationSimulation({ onComplete }: ConsultationSimulationProps) {
  const [mode, setMode] = useState<SimulationMode>('select');
  const [currentStep, setCurrentStep] = useState<SimulationStep>('intro');
  const [isPaused, setIsPaused] = useState(false);
  const [chunks, setChunks] = useState<AudioChunkSimulation[]>(SIMULATED_CHUNKS);
  const [tasks, setTasks] = useState<TaskProgress[]>([
    { type: 'TRANSCRIPTION', status: 'pending', progress: 0, current_chunk: 0, total_chunks: 6 },
    { type: 'DIARIZATION', status: 'pending', progress: 0 },
    { type: 'SOAP_GENERATION', status: 'pending', progress: 0 },
    { type: 'ENCRYPTION', status: 'pending', progress: 0 },
  ]);
  const [currentMessage, setCurrentMessage] = useState<string>('');
  const [transcriptionResults, setTranscriptionResults] = useState<string[]>([]);
  const [showSOAPNotes, setShowSOAPNotes] = useState(false);

  /**
   * Update task status
   */
  const updateTask = useCallback((
    type: TaskProgress['type'],
    updates: Partial<TaskProgress>
  ) => {
    setTasks(prev =>
      prev.map(task =>
        task.type === type ? { ...task, ...updates } : task
      )
    );
  }, []);

  /**
   * Simulate upload step
   */
  const simulateUpload = useCallback(async () => {
    setCurrentMessage('Starting chunk upload...');

    for (let i = 0; i < chunks.length; i++) {
      if (isPaused) break;

      // Update chunk status
      setChunks(prev =>
        prev.map((chunk, idx) =>
          idx === i ? { ...chunk, status: 'uploading' } : chunk
        )
      );

      setCurrentMessage(PROGRESS_MESSAGES.upload[i]);

      await new Promise(resolve => setTimeout(resolve, LATENCY.upload_per_chunk));

      setChunks(prev =>
        prev.map((chunk, idx) =>
          idx === i ? { ...chunk, status: 'success' } : chunk
        )
      );
    }

    setCurrentMessage('All chunks uploaded successfully ✅');
    await new Promise(resolve => setTimeout(resolve, 500));
    setCurrentStep('checkpoint');
  }, [chunks.length, isPaused]);

  /**
   * Simulate checkpoint (concatenate chunks)
   */
  const simulateCheckpoint = useCallback(async () => {
    setCurrentMessage('Concatenating audio chunks...');
    await new Promise(resolve => setTimeout(resolve, LATENCY.checkpoint));
    setCurrentMessage('Audio checkpoint created ✅');
    await new Promise(resolve => setTimeout(resolve, 500));
    setCurrentStep('transcription');
  }, []);

  /**
   * Simulate transcription step
   */
  const simulateTranscription = useCallback(async () => {
    updateTask('TRANSCRIPTION', { status: 'in_progress', progress: 0 });
    setCurrentMessage('Starting transcription...');

    for (let i = 0; i < SIMULATED_TRANSCRIPTIONS.length; i++) {
      if (isPaused) break;

      const transcription = SIMULATED_TRANSCRIPTIONS[i];
      setCurrentMessage(PROGRESS_MESSAGES.transcription[i]);

      // Simulate transcription delay
      await new Promise(resolve => setTimeout(resolve, LATENCY.transcription_per_chunk));

      // Add transcription result
      setTranscriptionResults(prev => [...prev, transcription.text]);

      // Update progress
      const progress = Math.round(((i + 1) / SIMULATED_TRANSCRIPTIONS.length) * 100);
      updateTask('TRANSCRIPTION', {
        progress,
        current_chunk: i + 1,
        message: `Chunk ${i + 1}/${SIMULATED_TRANSCRIPTIONS.length} transcribed (${transcription.confidence * 100}% confidence)`,
      });
    }

    updateTask('TRANSCRIPTION', { status: 'completed', progress: 100 });
    setCurrentMessage('Transcription completed ✅');
    await new Promise(resolve => setTimeout(resolve, 500));
    setCurrentStep('diarization');
  }, [isPaused, updateTask]);

  /**
   * Simulate diarization step
   */
  const simulateDiarization = useCallback(async () => {
    updateTask('DIARIZATION', { status: 'in_progress', progress: 0 });
    setCurrentMessage(PROGRESS_MESSAGES.diarization);

    // Simulate progress increments
    for (let i = 0; i <= 100; i += 20) {
      await new Promise(resolve => setTimeout(resolve, LATENCY.diarization_total / 5));
      updateTask('DIARIZATION', { progress: i });
    }

    updateTask('DIARIZATION', {
      status: 'completed',
      progress: 100,
      message: `${SIMULATED_DIARIZATION.length} segments identified (Médico/Paciente)`,
    });
    setCurrentMessage('Diarization completed ✅');
    await new Promise(resolve => setTimeout(resolve, 500));
    setCurrentStep('soap');
  }, [updateTask]);

  /**
   * Simulate SOAP generation step
   */
  const simulateSOAPGeneration = useCallback(async () => {
    updateTask('SOAP_GENERATION', { status: 'in_progress', progress: 0 });
    setCurrentMessage(PROGRESS_MESSAGES.soap);

    // Simulate progress increments
    for (let i = 0; i <= 100; i += 25) {
      await new Promise(resolve => setTimeout(resolve, LATENCY.soap_generation / 4));
      updateTask('SOAP_GENERATION', { progress: i });
    }

    updateTask('SOAP_GENERATION', {
      status: 'completed',
      progress: 100,
      message: `SOAP notes generated (${SIMULATED_SOAP.completeness}% completeness)`,
    });
    setCurrentMessage('SOAP generation completed ✅');
    setShowSOAPNotes(true);
    await new Promise(resolve => setTimeout(resolve, 500));
    setCurrentStep('export');
  }, [updateTask]);

  /**
   * Execute current step based on mode
   */
  useEffect(() => {
    if (mode === 'select' || isPaused) return;

    const executeStep = async () => {
      switch (currentStep) {
        case 'intro':
          await new Promise(resolve => setTimeout(resolve, 1000));
          setCurrentStep('upload');
          break;
        case 'upload':
          await simulateUpload();
          break;
        case 'checkpoint':
          await simulateCheckpoint();
          break;
        case 'transcription':
          await simulateTranscription();
          break;
        case 'diarization':
          await simulateDiarization();
          break;
        case 'soap':
          await simulateSOAPGeneration();
          break;
        case 'export':
          // In auto mode, automatically mark encryption as completed and finish
          if (mode === 'auto') {
            updateTask('ENCRYPTION', { status: 'completed', progress: 100 });
            setCurrentMessage('Encryption completed ✅');
            await new Promise(resolve => setTimeout(resolve, 1000));
            setCurrentStep('complete');
          }
          // In guided/hands-on modes, wait for user to click button
          break;
      }
    };

    if (mode === 'auto') {
      executeStep();
    }
  }, [currentStep, mode, isPaused, updateTask, simulateUpload, simulateCheckpoint, simulateTranscription, simulateDiarization, simulateSOAPGeneration]);

  /**
   * Handle manual step execution (guided/hands-on modes)
   */
  const executeNextStep = async () => {
    switch (currentStep) {
      case 'intro':
        setCurrentStep('upload');
        break;
      case 'upload':
        await simulateUpload();
        break;
      case 'checkpoint':
        await simulateCheckpoint();
        break;
      case 'transcription':
        await simulateTranscription();
        break;
      case 'diarization':
        await simulateDiarization();
        break;
      case 'soap':
        await simulateSOAPGeneration();
        break;
      case 'export':
        setCurrentStep('complete');
        break;
    }
  };

  /**
   * Render mode selection
   */
  if (mode === 'select') {
    return (
      <div className="space-y-6 max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h3 className="text-2xl font-bold text-slate-50 mb-2">
            🎬 Selecciona el modo de simulación
          </h3>
          <p className="text-slate-400">
            Experimenta el flujo completo de AURITY sin audio real
          </p>
        </div>

        {/* Mode Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Auto-play */}
          <Button
            onClick={() => setMode('auto')}
            className="p-6 bg-slate-900/50 border-2 border-slate-700/50 hover:border-cyan-500/50 rounded-xl transition-all group"
            variant="ghost"
            size="lg"
            title="Auto-play"
          >
            <div className="text-4xl mb-4">⏯️</div>
            <h4 className="fi-section-title">Auto-play</h4>
            <p className="fi-subtitle mb-4">
              Observa el flujo completo sin interacción
            </p>
            <div className="flex items-center justify-between text-xs">
              <span className="fi-text-info">~2 minutos</span>
              <span className="text-slate-500">Pasivo</span>
            </div>
          </Button>

          {/* Guided */}
          <Button
            onClick={() => setMode('guided')}
            className="p-6 bg-slate-900/50 border-2 border-slate-700/50 hover:border-purple-500/50 rounded-xl transition-all group"
            variant="ghost"
            size="lg"
            title="Guided"
          >
            <div className="text-4xl mb-4">🧭</div>
            <h4 className="fi-section-title">Guided</h4>
            <p className="fi-subtitle mb-4">
              FI te guía paso a paso con explicaciones
            </p>
            <div className="flex items-center justify-between text-xs">
              <span className="fi-text-purple">~5 minutos</span>
              <span className="text-slate-500">Interactivo</span>
            </div>
          </Button>

          {/* Hands-on */}
          <Button
            onClick={() => setMode('hands-on')}
            className="p-6 bg-slate-900/50 border-2 border-slate-700/50 hover:border-emerald-500/50 rounded-xl transition-all group"
            variant="ghost"
            size="lg"
            title="Hands-on"
          >
            <div className="text-4xl mb-4">🎮</div>
            <h4 className="fi-section-title">Hands-on</h4>
            <p className="fi-subtitle mb-4">
              Ejecuta cada paso manualmente con total control
            </p>
            <div className="flex items-center justify-between text-xs">
              <span className="fi-text-success">~10 minutos</span>
              <span className="text-slate-500">Experimental</span>
            </div>
          </Button>
        </div>

        {/* Info Box */}
        <div className="p-6 bg-blue-950/20 border border-blue-700/30 rounded-xl">
          <p className="text-sm text-blue-300 flex items-start gap-3">
            <span className="text-2xl">💡</span>
            <span>
              <strong>Nota:</strong> Esta simulación usa datos precargados y no requiere conexión al backend.
              Los tiempos y resultados son ficticios para fines educativos.
            </span>
          </p>
        </div>
      </div>
    );
  }

  /**
   * Render simulation interface
   */
  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="fi-flex-between">
        <div>
          <h3 className="text-xl font-bold text-slate-50">
            Consulta Médica Simulada
          </h3>
          <p className="fi-subtitle">
            Modo: <span className="fi-text-info capitalize">{mode}</span> ·
            Step: <span className="fi-text-purple capitalize">{currentStep.replace(/_/g, ' ')}</span>
          </p>
        </div>

        {/* Controls */}
        <div className="fi-flex-gap-md">
          {mode === 'auto' && currentStep !== 'complete' && (
            <Button
              onClick={() => setIsPaused(!isPaused)}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition-colors flex items-center gap-2"
              variant="ghost"
              size="sm"
              title={isPaused ? 'Resume' : 'Pause'}
            >
              {isPaused ? '▶️ Resume' : '⏸️ Pause'}
            </Button>
          )}
          <Button
            onClick={() => {
              setMode('select');
              setCurrentStep('intro');
              setIsPaused(false);
            }}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition-colors"
            variant="ghost"
            size="sm"
            title="Change Mode"
          >
            🔄 Change Mode
          </Button>
        </div>
      </div>

      {/* Main Grid: Progress Monitor + Results */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Progress Monitor */}
        <div className="bg-slate-900/50 p-6 rounded-xl border border-slate-700/50">
          <ProgressMonitor tasks={tasks} currentMessage={currentMessage} />
        </div>

        {/* Right: Results Panel */}
        <div className="bg-slate-900/50 p-6 rounded-xl border border-slate-700/50 space-y-4">
          <h4 className="text-lg font-semibold text-slate-200 fi-border-bottom/50 pb-2">
            📄 Results
          </h4>

          {/* Transcription Results */}
          {transcriptionResults.length > 0 && (
            <div className="fi-stack-sm">
              <p className="text-sm font-semibold fi-text-info">Transcriptions:</p>
              <div className="max-h-64 overflow-y-auto space-y-2 pr-2">
                {transcriptionResults.map((text, idx) => (
                  <div key={idx} className="p-3 bg-slate-950/40 rounded-lg border border-slate-700/30">
                    <p className="text-xs fi-text">{text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* SOAP Notes */}
          {showSOAPNotes && (
            <div className="space-y-3">
              <p className="text-sm font-semibold fi-text-success">SOAP Notes Generated:</p>
              <div className="p-4 bg-emerald-950/20 border border-emerald-700/30 rounded-lg space-y-3">
                <div>
                  <p className="text-xs font-semibold text-emerald-300">Subjetivo:</p>
                  <p className="text-xs fi-text mt-1">{SIMULATED_SOAP.subjetivo.substring(0, 150)}...</p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-cyan-300">Objetivo:</p>
                  <p className="text-xs fi-text mt-1">{SIMULATED_SOAP.objetivo.substring(0, 100)}...</p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-purple-300">Análisis:</p>
                  <p className="text-xs fi-text mt-1">{SIMULATED_SOAP.analisis.substring(0, 100)}...</p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-yellow-300">Plan:</p>
                  <p className="text-xs fi-text mt-1">{SIMULATED_SOAP.plan.substring(0, 100)}...</p>
                </div>
                <p className="fi-text-xs text-right">
                  Completeness: <span className="fi-text-success font-semibold">{SIMULATED_SOAP.completeness}%</span>
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Step Control (for guided/hands-on modes) */}
      {(mode === 'guided' || mode === 'hands-on') && currentStep !== 'complete' && currentStep !== 'intro' && (
        <div className="text-center">
          <Button
            onClick={executeNextStep}
            disabled={isPaused}
            className="fi-btn-cta-xl-cyan"
            variant="primary"
            size="xl"
            title="Execute step"
          >
            {currentStep === 'export' ? 'Export Evidence' : `Execute: ${currentStep.replace(/_/g, ' ')}`} →
          </Button>
        </div>
      )}

      {/* Completion */}
      {currentStep === 'complete' && (
        <div className="text-center space-y-4">
          <div className="text-6xl">🎉</div>
          <h3 className="text-2xl font-bold fi-text-success">Simulación Completada</h3>
          <p className="fi-text">
            Has experimentado el flujo completo de AURITY: Upload → Transcription → Diarization → SOAP → Export
          </p>
          <Button onClick={onComplete} size="xl">
            Continuar al siguiente paso →
          </Button>
        </div>
      )}
    </div>
  );
}
