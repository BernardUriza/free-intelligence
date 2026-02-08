/**
 * DemoConsultationModal Component
 *
 * Interactive demo modal that simulates consultation workflow:
 * 1. Shows dialogue line-by-line (editable)
 * 2. User clicks "Enviar" → TTS generates audio + sends chunk to backend
 * 3. Audio plays while chunk is processed (transcription, diarization)
 * 4. Simulates complete recording workflow without microphone
 *
 * Created: 2025-11-17
 */

'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { X, Send, Mic, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DEMO_CONSULTATION } from '@/lib/demo/consultation-script';
import { toastError } from '@/lib/swal';
import { getBackendUrl } from '@/lib/api/client';
import { ROUTES } from '@/lib/api/routes';

interface DemoConsultationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSendChunk: (audioBlob: Blob, lineIndex: number) => Promise<void>;
  isProcessing: boolean;
}

export function DemoConsultationModal({
  isOpen,
  onClose,
  onSendChunk,
  isProcessing,
}: DemoConsultationModalProps) {
  const [currentLineIndex, setCurrentLineIndex] = useState(0);
  const [editedText, setEditedText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentAudio, setCurrentAudio] = useState<HTMLAudioElement | null>(null);

  const currentLine = DEMO_CONSULTATION[currentLineIndex];
  const isLastLine = currentLineIndex === DEMO_CONSULTATION.length - 1;

  // Initialize edited text when line changes
  const resetEditedText = useCallback(() => {
    if (currentLine) {
      setEditedText(currentLine.text);
    }
  }, [currentLine]);

  // Reset when modal opens
  const handleOpen = useCallback(() => {
    if (isOpen && currentLineIndex === 0) {
      resetEditedText();
    }
  }, [isOpen, currentLineIndex, resetEditedText]);

  // Effect to reset text when line changes or modal opens
  useEffect(() => {
    handleOpen();
  }, [handleOpen]);

  useEffect(() => {
    resetEditedText();
  }, [currentLineIndex, resetEditedText]);

  // Generate TTS audio and send as chunk
  const handleSendLine = async () => {
    if (!editedText.trim() || isGenerating || isProcessing) return;

    setIsGenerating(true);

    try {
      // 1. Call TTS endpoint to generate audio
      // Note: TTS returns binary audio blob, not JSON - requires direct fetch
      console.log(`[Demo] Generating TTS for line ${currentLineIndex + 1}...`);
      const backendUrl = getBackendUrl();

      const ttsResponse = await fetch(`${backendUrl}${ROUTES.tts}/synthesize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: editedText,
          voice: currentLine.speaker === 'doctor' ? 'alloy' : 'nova',
          speed: 0.9,
        }),
      });

      if (!ttsResponse.ok) {
        throw new Error(`TTS failed: ${ttsResponse.status}`);
      }

      const audioBlob = await ttsResponse.blob();
      console.log(`[Demo] TTS generated: ${(audioBlob.size / 1024).toFixed(2)} KB`);

      // 2. Play audio for user feedback
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      setCurrentAudio(audio);

      audio.play();
      console.log('[Demo] Playing TTS audio...');

      // 3. Send audio chunk to backend (simulates real recording)
      await onSendChunk(audioBlob, currentLineIndex);

      // 4. Wait for audio to finish playing
      await new Promise<void>((resolve) => {
        audio.onended = () => {
          URL.revokeObjectURL(audioUrl);
          setCurrentAudio(null);
          resolve();
        };

        audio.onerror = () => {
          URL.revokeObjectURL(audioUrl);
          setCurrentAudio(null);
          resolve();
        };
      });

      // 5. Apply natural pause if specified
      if (currentLine.pauseAfterMs && currentLine.pauseAfterMs > 0) {
        console.log(`[Demo] Pausing ${currentLine.pauseAfterMs}ms...`);
        await new Promise((resolve) => setTimeout(resolve, currentLine.pauseAfterMs));
      }

      // 6. Move to next line
      if (!isLastLine) {
        setCurrentLineIndex((prev) => prev + 1);
      } else {
        console.log('[Demo] Consultation complete');
        // Keep modal open on last line so user can review
      }
    } catch (error) {
      console.error('[Demo] Error generating/sending line:', error);
      toastError(error instanceof Error ? error.message : 'Error desconocido');
    } finally {
      setIsGenerating(false);
    }
  };

  // Stop audio playback
  const handleStopAudio = () => {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      setCurrentAudio(null);
    }
  };

  // Reset demo
  const handleReset = () => {
    handleStopAudio();
    setCurrentLineIndex(0);
    setEditedText(DEMO_CONSULTATION[0].text);
  };

  if (!isOpen) return null;

  return (
    <div className="fi-modal-backdrop">
      <div className="med-demo-modal">
        {/* Header */}
        <div className="flex items-center justify-between p-6 fi-border-bottom">
          <div>
            <h2 className="fi-title-xl">Demo Consulta Médica</h2>
            <p className="fi-subtitle mt-1">
              Línea {currentLineIndex + 1} de {DEMO_CONSULTATION.length}
            </p>
          </div>
          <Button
            onClick={() => {
              handleStopAudio();
              onClose();
            }}
            variant="ghost"
            size="sm"
            icon={X}
            aria-label="Cerrar"
          />
        </div>

        {/* Progress bar */}
        <div className="h-2 bg-slate-800">
          <div
            className="h-full bg-gradient-to-r from-cyan-500 to-purple-500 transition-all duration-300"
            style={{
              width: `${((currentLineIndex + 1) / DEMO_CONSULTATION.length) * 100}%`,
            }}
          />
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Speaker indicator */}
          <div className="fi-flex-gap-md">
            {currentLine.speaker === 'doctor' ? (
              <>
                <div className="fi-info-block-cyan">
                  <User className="h-5 w-5 fi-text-info" />
                </div>
                <div>
                  <p className="text-sm font-medium fi-text-info">Doctor</p>
                  <p className="fi-text-xs-muted">Voz: Alloy (masculina)</p>
                </div>
              </>
            ) : (
              <>
                <div className="fi-info-block-purple">
                  <Mic className="h-5 w-5 fi-text-purple" />
                </div>
                <div>
                  <p className="text-sm font-medium fi-text-purple">Paciente</p>
                  <p className="fi-text-xs-muted">Voz: Nova (femenina)</p>
                </div>
              </>
            )}
          </div>

          {/* Editable text area */}
          <div>
            <label className="fi-label">
              Texto a sintetizar (editable):
            </label>
            <textarea
              value={editedText}
              onChange={(e) => setEditedText(e.target.value)}
              disabled={isGenerating || isProcessing}
              className="fi-input-cyan h-32 resize-none fi-disabled"
              placeholder="Escribe el texto para la línea de diálogo..."
            />
            <p className="fi-text-xs-muted mt-2">
              {editedText.length} caracteres (máx 4096)
            </p>
          </div>

          {/* Status indicators */}
          {isGenerating && (
            <div className="fi-info-block-amber flex items-center gap-2">
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-amber-500 border-t-transparent" />
              <span className="text-sm fi-text-warning">Generando audio con TTS...</span>
            </div>
          )}

          {isProcessing && (
            <div className="fi-info-block-cyan flex items-center gap-2">
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-cyan-500 border-t-transparent" />
              <span className="text-sm fi-text-info">Procesando chunk (transcripción)...</span>
            </div>
          )}

          {currentAudio && (
            <div className="fi-info-block-purple flex items-center gap-2">
              <div className="animate-pulse h-4 w-4 bg-purple-500 rounded-full" />
              <span className="text-sm fi-text-purple">Reproduciendo audio...</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 fi-border-top bg-slate-800/50">
          <Button
            onClick={handleReset}
            disabled={isGenerating || isProcessing}
            variant="ghost"
          >
            Reiniciar
          </Button>

          <div className="flex gap-3">
            {currentAudio && (
              <Button
                onClick={handleStopAudio}
                variant="secondary"
              >
                Detener Audio
              </Button>
            )}

            <Button
              onClick={handleSendLine}
              disabled={
                !editedText.trim() ||
                isGenerating ||
                isProcessing ||
                editedText.length > 4096
              }
              icon={Send}
              className="med-btn-gradient-cp"
            >
              {isLastLine ? 'Enviar y Finalizar' : 'Enviar Línea'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
