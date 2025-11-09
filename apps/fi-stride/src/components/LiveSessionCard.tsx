/**
 * SESION-04/06: Live athlete session component (Enhanced with TTS + Encryption)
 * AC: Cronómetro + conteo de reps + check-in emocional + KATNISS suggestions
 * SESION-06: Azure TTS + segment encryption + dead-drop relay
 * No penalties - only positive feedback
 */

'use client';

import React, { useState, useEffect, useRef } from 'react';
import { T21Button } from './T21Button';
import { T21Card } from './T21Card';
import { T21Modal } from './T21Modal';
import { Pictogram, Pictograms } from './Pictograms';
import { useAudioCache } from '../hooks/useAudioCache';
import { encryptAndUploadSegment } from '../lib/encryptAndUpload';
import sesion06Config from '../config/sesion-06.config';
import type { SegmentData } from '../lib/encryptAndUpload';

interface LiveSessionProps {
  athleteId: string;
  exerciseName: string;
  targetReps?: number;
  maxHeartRate?: number;
  sessionId?: string; // Backend session ID
  onSessionEnd: (data: SessionData) => void;
}

interface SessionData {
  athleteId: string;
  exerciseName: string;
  repsCompleted: number;
  sessionTime: number;
  emotionalCheck: 1 | 2 | 3 | 4 | 5;
  timestamp: string;
  heartRateAvg?: number;
}

const EmotionalScale = [
  { emoji: '😴', label: 'Muy cansado', value: 1 },
  { emoji: '😔', label: 'Cansado', value: 2 },
  { emoji: '😐', label: 'Normal', value: 3 },
  { emoji: '😊', label: 'Bien', value: 4 },
  { emoji: '🤩', label: 'Excelente', value: 5 },
];

export const LiveSessionCard: React.FC<LiveSessionProps> = ({
  athleteId,
  exerciseName,
  targetReps = 20,
  maxHeartRate,
  sessionId,
  onSessionEnd,
}) => {
  const [reps, setReps] = useState(0);
  const [sessionTime, setSessionTime] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [emotionalCheck, setEmotionalCheck] = useState<1 | 2 | 3 | 4 | 5>(3);
  const [showEmotionalCheck, setShowEmotionalCheck] = useState(false);
  const [katnissMessage, setKatnissMessage] = useState('');
  const [heartRate] = useState(0);
  const [sessionStartId] = useState(() =>
    `session_${new Date().toISOString().replace(/[:-]/g, '').split('.')[0]}`
  );

  // Audio cache for pre-generated KATNISS phrases (rep counts, milestones, emotional feedback)
  const { isReady: audioReady, playAudio, loadCache } = useAudioCache();
  const segmentQueueRef = useRef<SegmentData[]>([]);

  // Load audio cache on session start
  useEffect(() => {
    if (isRunning && !audioReady) {
      loadCache().catch((err) => console.warn('Failed to load audio cache:', err));
    }
  }, [isRunning, audioReady, loadCache]);

  // Timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRunning) {
      interval = setInterval(() => {
        setSessionTime((prev) => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isRunning]);

  // Format time MM:SS
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Handle rep addition + backend sync + SESION-06 encryption
  const handleAddRep = async () => {
    const newReps = reps + 1;
    setReps(newReps);

    // Cancel any previous TTS to avoid overlapping
    window.speechSynthesis?.cancel();

    // Determine which cached audio to play (priority: milestones > count)
    let audioKey: string | null = null;
    let katnissMsg = '';

    if (newReps === 5) {
      audioKey = 'rep_5';
      katnissMsg = '¡Vas bien! Continúa así 💪';
    } else if (newReps === 10) {
      audioKey = 'rep_10';
      katnissMsg = '¡Mitad del camino! ¡Sigue adelante! 🔥';
    } else if (newReps === targetReps) {
      audioKey = `rep_${targetReps}`;
      katnissMsg = '¡LO HICISTE! 🏆 ¡Eres un campeón!';
    } else if (newReps <= 20) {
      // Use pre-generated audio for reps 1-4, 6-9, 11-19
      audioKey = `rep_${newReps}`;
    }

    // Play cached audio (instant, zero latency)
    if (audioReady && audioKey) {
      playAudio(audioKey).catch((err) => console.warn('Audio cache error:', err));
    }

    // Set KATNISS message
    if (katnissMsg) {
      setKatnissMessage(katnissMsg);
    }

    // Send to backend (optional - non-blocking)
    if (sessionId) {
      try {
        await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:7001/api'}/athlete-sessions/${sessionId}/rep`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rep_number: newReps, heart_rate: heartRate }),
          }
        );
      } catch (error) {
        console.error('Rep sync error:', error);
      }
    }

    // Queue segment for encryption and dead-drop upload
    const segment: SegmentData = {
      segment_id: `${sessionStartId}_rep_${newReps}`,
      timestamp: Date.now(),
      reps: newReps,
      rpe: emotionalCheck,
      heart_rate: heartRate || undefined,
      notes: `Rep ${newReps} completada`,
    };
    segmentQueueRef.current.push(segment);

    // Trigger encryption/upload if we have config
    if (sesion06Config.presign_url && sessionId) {
      encryptAndUploadSegment(segment, {
        presign_url: sesion06Config.presign_url,
        nas_spki_url: sesion06Config.nas_spki_url || '',
        segment_ms: sesion06Config.segment_ms,
      }).catch((err) => {
        console.warn('Encryption/upload error (will retry offline):', err);
      });
    }
  };


  // Handle emotional check-in + SESION-06 encryption
  const handleEmotionalCheckIn = async (value: 1 | 2 | 3 | 4 | 5) => {
    setEmotionalCheck(value);
    const feeling = EmotionalScale.find((s) => s.value === value)?.label;

    // Cancel any previous Web Speech audio
    window.speechSynthesis?.cancel();

    // KATNISS adaptive feedback - use pre-cached audio
    let audioKey: string | null = null;
    let katnissMsg = '';
    if (value <= 2) {
      audioKey = `feeling_${value}`;
      katnissMsg = 'Descansa cuando lo necesites. ¡Eres fuerte! 💪';
      setIsRunning(false);
    } else if (value === 3) {
      audioKey = 'feeling_3';
      katnissMsg = '¡Vamos! Un poco más 🌟';
    } else {
      audioKey = `feeling_${value}`;
      katnissMsg = '¡Wow! ¡Increíble energía! 🚀';
    }

    // Play cached audio - instant feedback
    if (audioReady && audioKey) {
      playAudio(audioKey).catch((err) => console.warn('Audio cache error:', err));
    }

    setKatnissMessage(katnissMsg);

    // Send to backend (optional - non-blocking)
    if (sessionId) {
      try {
        await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:7001/api'}/athlete-sessions/${sessionId}/emotional-check`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ feeling: value }),
          }
        );
      } catch (error) {
        console.error('Emotional check-in sync error:', error);
      }
    }

    // Queue RPE check as segment
    const rpeSegment: SegmentData = {
      segment_id: `${sessionStartId}_rpe_${value}`,
      timestamp: Date.now(),
      reps,
      rpe: value,
      heart_rate: heartRate || undefined,
      notes: `RPE check-in: ${feeling}`,
    };
    segmentQueueRef.current.push(rpeSegment);

    setShowEmotionalCheck(false);
  };

  // Handle session end + process all segments
  const handleSessionEnd = async () => {
    setIsRunning(false);

    // Cancel any previous Web Speech audio
    window.speechSynthesis?.cancel();

    // Completion message from cache
    if (audioReady) {
      playAudio('session_end').catch((err) => console.warn('Audio cache error:', err));
    }

    // Process any remaining segments in queue (offline-first)
    if (segmentQueueRef.current.length > 0 && sesion06Config.presign_url) {
      console.log(
        `Processing ${segmentQueueRef.current.length} queued segments...`
      );
      for (const seg of segmentQueueRef.current) {
        encryptAndUploadSegment(seg, {
          presign_url: sesion06Config.presign_url,
          nas_spki_url: sesion06Config.nas_spki_url || '',
          segment_ms: sesion06Config.segment_ms,
          offline_queue_name: 'offline_queue',
        }).catch((err) => {
          console.warn('Segment upload failed (queued for retry):', err);
        });
      }
    }

    const data: SessionData = {
      athleteId,
      exerciseName,
      repsCompleted: reps,
      sessionTime,
      emotionalCheck,
      timestamp: new Date().toISOString(),
      heartRateAvg: heartRate,
    };

    onSessionEnd(data);
  };

  return (
    <div className="space-y-6">
      {/* Main Display */}
      <T21Card title={exerciseName} icon={Pictograms.PLAY} color="blue">
        {/* Timer */}
        <div className="text-center mb-6">
          <div className="text-6xl font-bold text-blue-700 font-mono">
            {formatTime(sessionTime)}
          </div>
          <p className="text-2xl text-gray-700 mt-2">Tiempo de sesión</p>
        </div>

        {/* Rep Counter */}
        <div className="bg-white rounded-lg p-6 mb-6 border-4 border-blue-700">
          <div className="text-7xl font-bold text-center text-green-700 mb-4">
            {reps}
          </div>
          <p className="text-2xl text-center text-gray-700">
            de {targetReps} repeticiones
          </p>
          <div className="mt-6 w-full bg-gray-300 rounded-full h-6 overflow-hidden">
            <div
              className="bg-green-500 h-full transition-all duration-300 ease-out"
              style={{ width: `${(reps / targetReps) * 100}%` }}
            />
          </div>
        </div>

        {/* KATNISS Message */}
        {katnissMessage && (
          <div className="bg-purple-100 border-4 border-purple-700 rounded-lg p-4 mb-6">
            <p className="text-2xl text-purple-900 font-bold">
              {Pictograms.SMILE_GOOD} {katnissMessage}
            </p>
          </div>
        )}

        {/* Heart Rate Monitor (if device) */}
        {maxHeartRate && heartRate > 0 && (
          <div className="bg-red-50 border-4 border-red-700 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-3">
              <Pictogram icon="HEART" size="xl" animated />
              <div>
                <p className="text-2xl font-bold text-red-700">{heartRate} bpm</p>
                <p className="text-lg text-gray-700">
                  Máx seguro: {maxHeartRate} bpm
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="space-y-3">
          <T21Button
            onClick={handleAddRep}
            variant="success"
            size="2xl"
            icon={Pictograms.CHECK}
            ariaLabel="Agregar repetición"
          >
            Rep Hecha
          </T21Button>

          <div className="flex gap-3">
            <T21Button
              onClick={() => setIsRunning(!isRunning)}
              variant={isRunning ? 'warning' : 'primary'}
              size="xl"
              icon={isRunning ? Pictograms.PAUSE : Pictograms.PLAY}
              ariaLabel={isRunning ? 'Pausar' : 'Continuar'}
            >
              {isRunning ? 'Pausa' : 'Continuar'}
            </T21Button>

            <T21Button
              onClick={() => setShowEmotionalCheck(true)}
              variant="info"
              size="xl"
              icon={EmotionalScale.find((s) => s.value === emotionalCheck)?.emoji}
              ariaLabel="Cómo te sientes"
            >
              Cómo Estás
            </T21Button>
          </div>

          <T21Button
            onClick={handleSessionEnd}
            variant="success"
            size="xl"
            icon={Pictograms.TROPHY}
            ariaLabel="Terminar sesión"
          >
            Sesión Hecha
          </T21Button>
        </div>
      </T21Card>

      {/* Emotional Check-in Modal */}
      <T21Modal
        isOpen={showEmotionalCheck}
        title="¿Cómo te sientes?"
        onClose={() => setShowEmotionalCheck(false)}
        icon="😊"
      >
        <div className="space-y-4">
          {EmotionalScale.map((scale) => (
            <T21Button
              key={scale.value}
              onClick={() => handleEmotionalCheckIn(scale.value as 1 | 2 | 3 | 4 | 5)}
              variant="info"
              size="xl"
              icon={scale.emoji}
              ariaLabel={scale.label}
            >
              {scale.label}
            </T21Button>
          ))}
        </div>
      </T21Modal>
    </div>
  );
};
