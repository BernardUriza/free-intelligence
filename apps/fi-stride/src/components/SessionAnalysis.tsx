import { useState, useEffect } from 'react'
import katnissService, { SessionData, KATNISSResponse } from '../services/katnissService'

interface SessionDataFromLive {
  athleteId: string
  exerciseName: string
  repsCompleted: number
  sessionTime: number
  emotionalCheck: 1 | 2 | 3 | 4 | 5
  timestamp: string
  heartRateAvg?: number
}

interface SessionAnalysisProps {
  athleteName?: string
  sessionData?: SessionDataFromLive | null
  onComplete?: (analysis: KATNISSResponse) => void
}

const mapEmotionalCheckToLabel = (emotionalCheck: number): 'happy' | 'neutral' | 'tired' => {
  if (emotionalCheck >= 4) return 'happy'
  if (emotionalCheck === 3) return 'neutral'
  return 'tired'
}

export function SessionAnalysis({ athleteName = 'Deportista', sessionData, onComplete }: SessionAnalysisProps) {
  const [step, setStep] = useState<'input' | 'loading' | 'result'>('input')
  const [formData, setFormData] = useState<{
    duration: number
    rpe: number
    emotionalCheckIn: 'happy' | 'neutral' | 'tired'
    notes: string
  }>({
    duration: 30,
    rpe: 5,
    emotionalCheckIn: 'neutral',
    notes: ''
  })

  // Initialize form with data from LiveSessionCard if provided
  useEffect(() => {
    if (sessionData) {
      setFormData({
        duration: Math.ceil(sessionData.sessionTime / 60),
        rpe: Math.min(10, Math.ceil((sessionData.repsCompleted / 20) * 10)),
        emotionalCheckIn: mapEmotionalCheckToLabel(sessionData.emotionalCheck),
        notes: `${sessionData.exerciseName}: ${sessionData.repsCompleted} reps completadas`
      })
    }
  }, [sessionData])
  const [result, setResult] = useState<KATNISSResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const emotionEmojis = {
    happy: '😊',
    neutral: '😐',
    tired: '😴'
  }

  const emotionLabels = {
    happy: 'Feliz',
    neutral: 'Normal',
    tired: 'Cansado'
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setStep('loading')
    setError(null)

    try {
      const sessionData: SessionData = {
        ...formData,
        athleteName
      }

      const analysis = await katnissService.analyzeSession(sessionData)
      setResult(analysis)
      setStep('result')

      if (onComplete) {
        onComplete(analysis)
      }

      await saveAnalysisToIndexedDB(analysis)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error analizando sesión')
      setStep('input')
    }
  }

  const saveAnalysisToIndexedDB = async (analysis: KATNISSResponse) => {
    try {
      const request = indexedDB.open('FIStride', 1)
      request.onsuccess = (event) => {
        const db = (event.target as IDBOpenDBRequest).result
        const transaction = db.transaction(['session_analysis'], 'readwrite')
        const store = transaction.objectStore('session_analysis')
        store.add({
          id: `analysis-${Date.now()}`,
          sessionData: formData,
          result: analysis,
          timestamp: new Date()
        })
      }
    } catch (err) {
      console.error('Failed to save analysis:', err)
    }
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      {step === 'input' && (
        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 space-y-6">
          <h2 className="text-3xl font-bold text-gray-900">¿Cómo te fue en la sesión?</h2>

          {/* Duration */}
          <div>
            <label className="block text-sm font-semibold text-gray-900 mb-3">
              Duración: <span className="text-blue-600">{formData.duration} min</span>
            </label>
            <input
              type="range"
              min="5"
              max="120"
              step="5"
              value={formData.duration}
              onChange={(e) =>
                setFormData({ ...formData, duration: Number(e.target.value) })
              }
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>5 min</span>
              <span>120 min</span>
            </div>
          </div>

          {/* RPE */}
          <div>
            <label className="block text-sm font-semibold text-gray-900 mb-3">
              ¿Cuánto esfuerzo hiciste? (1-10)
            </label>
            <div className="grid grid-cols-5 gap-2">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                <button
                  key={num}
                  type="button"
                  onClick={() => setFormData({ ...formData, rpe: num })}
                  className={`py-2 rounded-lg font-bold transition-all ${
                    formData.rpe === num
                      ? 'bg-blue-600 text-white ring-2 ring-blue-400'
                      : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                  }`}
                >
                  {num}
                </button>
              ))}
            </div>
          </div>

          {/* Emotional Check-in */}
          <div>
            <label className="block text-sm font-semibold text-gray-900 mb-3">
              ¿Cómo te sientes ahora?
            </label>
            <div className="grid grid-cols-3 gap-3">
              {(['happy', 'neutral', 'tired'] as const).map((emotion) => (
                <button
                  key={emotion}
                  type="button"
                  onClick={() =>
                    setFormData({ ...formData, emotionalCheckIn: emotion })
                  }
                  className={`py-4 px-3 rounded-lg font-semibold transition-all flex flex-col items-center gap-2 ${
                    formData.emotionalCheckIn === emotion
                      ? 'bg-blue-600 text-white ring-2 ring-blue-400'
                      : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                  }`}
                >
                  <span className="text-3xl">{emotionEmojis[emotion]}</span>
                  <span className="text-sm">{emotionLabels[emotion]}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Notes */}
          <div>
            <label htmlFor="notes" className="block text-sm font-semibold text-gray-900 mb-2">
              Notas (opcional)
            </label>
            <textarea
              id="notes"
              value={formData.notes}
              onChange={(e) =>
                setFormData({ ...formData, notes: e.target.value })
              }
              placeholder="¿Algo más que quieras contar?"
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none transition"
            />
          </div>

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="w-full py-3 px-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-blue-700 transition-all"
          >
            🤖 Obtener Feedback de KATNISS
          </button>
        </form>
      )}

      {step === 'loading' && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-blue-100 mb-4 animate-spin">
            <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full"></div>
          </div>
          <p className="text-lg font-semibold text-gray-900">🤖 KATNISS analizando tu sesión...</p>
          <p className="text-gray-600 mt-2">Por favor espera un momento</p>
        </div>
      )}

      {step === 'result' && result && (
        <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg shadow-sm border-2 border-purple-200 p-8 space-y-6">
          <h2 className="text-3xl font-bold text-gray-900 text-center">✨ Feedback de KATNISS ✨</h2>

          <div className="space-y-6">
            {/* Motivation Section */}
            <div className="bg-white rounded-lg p-6 border border-purple-200">
              <h3 className="text-xl font-bold text-purple-600 mb-4">💪 Motivación</h3>
              <p className="text-gray-700 leading-relaxed text-lg italic">
                {result.motivation}
              </p>
            </div>

            {/* Suggestion Section */}
            <div className="bg-white rounded-lg p-6 border border-blue-200 space-y-3">
              <h3 className="text-xl font-bold text-blue-600 mb-4">💡 Próxima Sesión</h3>
              <p className="text-gray-700 leading-relaxed">
                {result.nextSuggestion}
              </p>
              <p className="text-gray-700 font-semibold">
                📅 Te recomendamos entrenar {result.dayRecommended}
              </p>
            </div>
          </div>

          <button
            onClick={() => {
              setStep('input')
              setFormData({
                duration: 30,
                rpe: 5,
                emotionalCheckIn: 'neutral',
                notes: ''
              })
            }}
            className="w-full py-3 px-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-blue-700 transition-all"
          >
            ➕ Otra Sesión
          </button>
        </div>
      )}
    </div>
  )
}
