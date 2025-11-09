/**
 * SESION-05: Post-session KATNISS analysis + motivation
 * AC: Resume de sesión + Ollama analysis + personalized encouragement + goal progress
 */

'use client';

import { useState, useEffect } from 'react';
import { T21Button } from './T21Button';
import { T21Card } from './T21Card';
import { Pictogram, Pictograms } from './Pictograms';

interface SessionData {
  athleteId: string;
  exerciseName: string;
  repsCompleted: number;
  sessionTime: number;
  emotionalCheck: 1 | 2 | 3 | 4 | 5;
  timestamp: string;
  heartRateAvg?: number;
}

interface PostSessionProps {
  sessionData: SessionData;
  goalStats?: {
    totalReps: number;
    weeklyAverage: number;
    personalRecord: number;
  };
  onContinue: () => void;
}

const EmotionalEmojis: Record<number, string> = {
  1: '😴',
  2: '😔',
  3: '😐',
  4: '😊',
  5: '🤩',
};

export const PostSessionAnalysis: React.FC<PostSessionProps> = ({
  sessionData,
  goalStats,
  onContinue,
}) => {
  const [katnissAnalysis, setKatnissAnalysis] = useState('');
  const [loading, setLoading] = useState(true);
  const [achievement, setAchievement] = useState<string>('');

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  // Fetch Ollama analysis on mount
  useEffect(() => {
    const fetchAnalysis = async () => {
      try {
        // Simulate Ollama API call (replace with actual endpoint)
        const prompt = `
        Athlete performance: ${sessionData.repsCompleted} reps in ${formatTime(sessionData.sessionTime)}.
        Emotional state: ${sessionData.emotionalCheck}/5.
        Exercise: ${sessionData.exerciseName}.

        Provide a brief, encouraging 1-2 sentence analysis in Spanish. Be positive, no criticism.
        `;

        // TODO: Replace with actual Ollama endpoint
        // const response = await fetch('/api/ollama/analyze', { method: 'POST', body: JSON.stringify({ prompt }) });

        // Placeholder response
        const analysis =
          sessionData.repsCompleted >= 15
            ? '¡Excelente trabajo! Tu esfuerzo y dedicación son increíbles. Eres más fuerte cada día.'
            : '¡Buen trabajo! Cada repetición te hace más fuerte. Sigue adelante.';

        setKatnissAnalysis(analysis);
        speak(analysis);

        // Determine achievement
        if (sessionData.repsCompleted === goalStats?.personalRecord) {
          setAchievement('🏆 ¡NUEVO RÉCORD PERSONAL! 🏆');
        } else if (sessionData.repsCompleted >= (goalStats?.totalReps || 20)) {
          setAchievement('🎉 ¡OBJETIVO ALCANZADO! 🎉');
        } else if (sessionData.repsCompleted >= 15) {
          setAchievement('🌟 ¡SESIÓN EXCELENTE! 🌟');
        }
      } catch (error) {
        console.error('Failed to fetch analysis:', error);
        setKatnissAnalysis(
          '¡Bien hecho! ¡Estamos orgullosos de tu esfuerzo!'
        );
      } finally {
        setLoading(false);
      }
    };

    fetchAnalysis();
  }, [sessionData, goalStats, speak]);

  return (
    <div className="space-y-6">
      {/* Achievement Banner */}
      {achievement && (
        <div className="bg-gradient-to-r from-yellow-400 to-orange-400 rounded-lg p-6 border-4 border-yellow-700">
          <div className="text-center">
            <p className="text-5xl font-bold text-gray-900 animate-bounce">
              {achievement}
            </p>
          </div>
        </div>
      )}

      {/* Session Summary */}
      <T21Card title="Resumen de Sesión" icon={Pictograms.CHECK} color="green">
        <div className="grid grid-cols-2 gap-4 mb-6">
          {/* Reps */}
          <div className="bg-green-100 rounded-lg p-4 border-4 border-green-700">
            <p className="text-4xl font-bold text-green-700">
              {sessionData.repsCompleted}
            </p>
            <p className="text-xl text-gray-700 mt-2">Repeticiones</p>
          </div>

          {/* Time */}
          <div className="bg-blue-100 rounded-lg p-4 border-4 border-blue-700">
            <p className="text-4xl font-bold text-blue-700">
              {formatTime(sessionData.sessionTime)}
            </p>
            <p className="text-xl text-gray-700 mt-2">Tiempo Total</p>
          </div>

          {/* Effort */}
          <div className="bg-purple-100 rounded-lg p-4 border-4 border-purple-700 col-span-2">
            <div className="flex items-center justify-between">
              <p className="text-2xl text-gray-700">Cómo te sentiste:</p>
              <p className="text-5xl">{EmotionalEmojis[sessionData.emotionalCheck]}</p>
            </div>
          </div>
        </div>

        {/* Heart Rate (if available) */}
        {sessionData.heartRateAvg && (
          <div className="bg-red-50 border-4 border-red-700 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-3">
              <Pictogram icon="HEART" size="lg" animated />
              <div>
                <p className="text-2xl font-bold text-red-700">
                  {sessionData.heartRateAvg} bpm promedio
                </p>
                <p className="text-lg text-gray-700">Ritmo cardíaco normal</p>
              </div>
            </div>
          </div>
        )}
      </T21Card>

      {/* KATNISS Analysis */}
      <T21Card title="Análisis KATNISS" icon="🤖" color="purple">
        {loading ? (
          <div className="text-center py-8">
            <p className="text-2xl text-gray-700 animate-pulse">
              KATNISS está pensando...
            </p>
          </div>
        ) : (
          <div>
            <p className="text-2xl text-gray-800 mb-6 leading-relaxed">
              {katnissAnalysis}
            </p>

            {/* Goal Progress */}
            {goalStats && (
              <div className="space-y-4 mt-6">
                <div>
                  <p className="text-xl font-bold text-gray-700 mb-2">
                    Progreso Semanal
                  </p>
                  <div className="bg-white rounded-lg border-4 border-purple-700 p-4">
                    <div className="flex justify-between mb-2">
                      <span className="text-lg text-gray-700">Promedio:</span>
                      <span className="text-2xl font-bold text-purple-700">
                        {goalStats.weeklyAverage.toFixed(1)}
                      </span>
                    </div>
                    <div className="w-full bg-gray-300 rounded-full h-4 overflow-hidden">
                      <div
                        className="bg-purple-500 h-full transition-all duration-500"
                        style={{
                          width: `${(goalStats.weeklyAverage / goalStats.totalReps) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>

                <div>
                  <p className="text-xl font-bold text-gray-700 mb-2">
                    Récord Personal
                  </p>
                  <div className="bg-white rounded-lg border-4 border-orange-700 p-4">
                    <div className="flex items-center gap-3">
                      <Pictogram icon="TROPHY" size="lg" />
                      <p className="text-2xl font-bold text-orange-700">
                        {goalStats.personalRecord} reps
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </T21Card>

      {/* Next Session Recommendation */}
      <T21Card
        title="Para la Próxima Sesión"
        icon={Pictograms.STAR}
        color="yellow"
      >
        <p className="text-2xl text-gray-800 mb-4">
          {sessionData.repsCompleted >= 20
            ? 'Intentemos aumentar 2-3 repeticiones más. ¡Eres fuerte! 💪'
            : 'Descansa bien y volveremos a intentarlo. ¡Cada día eres mejor! 🌟'}
        </p>
      </T21Card>

      {/* Continue Button */}
      <div className="flex gap-3">
        <T21Button
          onClick={onContinue}
          variant="success"
          size="2xl"
          icon={Pictograms.CHECK}
          ariaLabel="Continuar"
        >
          Continuar
        </T21Button>
      </div>
    </div>
  );
};
