import React, { useState, useEffect } from 'react';
import { Exercise } from '../services/exerciseStorage';

interface ExerciseDetailViewProps {
  exercise: Exercise;
  onClose?: () => void;
}

export function ExerciseDetailView({ exercise, onClose }: ExerciseDetailViewProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [isDownloaded, setIsDownloaded] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

  // Check if exercise is downloaded
  useEffect(() => {
    const downloaded = localStorage.getItem(`exercise-downloaded-${exercise.id}`);
    setIsDownloaded(!!downloaded);
  }, [exercise.id]);

  const handleDownloadOffline = async () => {
    setIsDownloading(true);
    try {
      // Simulate download - in real app, would fetch video and store in IndexedDB
      await new Promise((resolve) => setTimeout(resolve, 1000));

      localStorage.setItem(`exercise-downloaded-${exercise.id}`, JSON.stringify({
        timestamp: new Date().toISOString(),
        metadata: exercise,
      }));

      setIsDownloaded(true);
    } catch (error) {
      console.error('Failed to download exercise:', error);
    } finally {
      setIsDownloading(false);
    }
  };

  const handleDeleteDownload = () => {
    localStorage.removeItem(`exercise-downloaded-${exercise.id}`);
    setIsDownloaded(false);
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-4">
      {/* Close Button */}
      {onClose && (
        <button
          onClick={onClose}
          className="mb-4 text-blue-400 hover:text-blue-300 flex items-center gap-1"
        >
          ← Volver
        </button>
      )}

      {/* Header */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 mb-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <div className="flex gap-2 text-4xl mb-2">
              {exercise.pictograms.map((p, i) => (
                <span key={i}>{p}</span>
              ))}
            </div>
            <h1 className="text-3xl font-bold">{exercise.title}</h1>
          </div>
        </div>

        <p className="text-slate-300 mb-4">{exercise.description}</p>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-700 p-3 rounded">
            <div className="text-2xl">⏱️</div>
            <div className="text-sm text-slate-400">Duración</div>
            <div className="font-bold">{Math.ceil(exercise.duration / 60)}min</div>
          </div>

          <div className="bg-slate-700 p-3 rounded">
            <div className="text-2xl">
              {exercise.difficulty === 'easy' ? '🟢' : exercise.difficulty === 'medium' ? '🟡' : '🔴'}
            </div>
            <div className="text-sm text-slate-400">Dificultad</div>
            <div className="font-bold capitalize">{exercise.difficulty}</div>
          </div>

          <div className="bg-slate-700 p-3 rounded">
            <div className="text-2xl">{isDownloaded ? '✅' : '⬇️'}</div>
            <div className="text-sm text-slate-400">Estado</div>
            <div className="font-bold text-sm">{isDownloaded ? 'Descargado' : 'No descargado'}</div>
          </div>

          <div className="bg-slate-700 p-3 rounded">
            <div className="text-2xl">🏷️</div>
            <div className="text-sm text-slate-400">Tags</div>
            <div className="font-bold text-sm">{exercise.tags.length} tags</div>
          </div>
        </div>
      </div>

      {/* Accessibility */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 mb-6">
        <h2 className="text-xl font-bold mb-4">♿ Accesibilidad</h2>
        <div className="grid grid-cols-2 gap-3">
          {exercise.accessibility.spacereduced && (
            <div className="flex items-center gap-2 bg-slate-700 p-3 rounded">
              <span className="text-xl">📏</span>
              <span>Espacio reducido</span>
            </div>
          )}
          {exercise.accessibility.chair && (
            <div className="flex items-center gap-2 bg-slate-700 p-3 rounded">
              <span className="text-xl">🪑</span>
              <span>En silla</span>
            </div>
          )}
          {exercise.accessibility.noEquipment && (
            <div className="flex items-center gap-2 bg-slate-700 p-3 rounded">
              <span className="text-xl">🆓</span>
              <span>Sin equipo</span>
            </div>
          )}
          {exercise.accessibility.lowImpact && (
            <div className="flex items-center gap-2 bg-slate-700 p-3 rounded">
              <span className="text-xl">💚</span>
              <span>Bajo impacto</span>
            </div>
          )}
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 mb-6">
        <h2 className="text-xl font-bold mb-4">📋 Instrucciones Paso a Paso</h2>
        <div className="space-y-3">
          {exercise.instructions.map((instruction, idx) => (
            <div
              key={idx}
              className={`flex gap-3 p-4 rounded-lg cursor-pointer transition-all ${
                currentStep === idx ? 'bg-blue-900 border-2 border-blue-500' : 'bg-slate-700 hover:bg-slate-600'
              }`}
              onClick={() => setCurrentStep(idx)}
            >
              <div className="text-2xl font-bold text-blue-400 min-w-8">{idx + 1}</div>
              <p>{instruction}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Safety Alerts */}
      {exercise.safetyAlerts.length > 0 && (
        <div className="bg-red-900 border-2 border-red-700 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <span>⚠️</span> Alertas de Seguridad
          </h2>
          <ul className="space-y-2">
            {exercise.safetyAlerts.map((alert, idx) => (
              <li key={idx} className="flex gap-2">
                <span className="text-red-400">•</span>
                <span>{alert}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Download/Delete Button */}
      {isDownloaded ? (
        <button
          onClick={handleDeleteDownload}
          className="w-full py-4 px-6 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg transition-colors"
        >
          🗑️ Eliminar Descarga
        </button>
      ) : (
        <button
          onClick={handleDownloadOffline}
          disabled={isDownloading}
          className="w-full py-4 px-6 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isDownloading ? '⏳ Descargando...' : '⬇️ Descargar para Offline'}
        </button>
      )}

      {/* Start Exercise Button */}
      <button className="w-full mt-3 py-4 px-6 bg-green-600 hover:bg-green-700 text-white font-bold rounded-lg transition-colors">
        ▶️ Iniciar Ejercicio
      </button>
    </div>
  );
}
