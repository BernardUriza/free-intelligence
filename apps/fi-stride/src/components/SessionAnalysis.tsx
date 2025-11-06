import { useState } from 'react'
import katnissService, { SessionData, KATNISSResponse } from '../services/katnissService'
import styles from '../styles/session-analysis.module.css'

interface SessionAnalysisProps {
  athleteName?: string
  onComplete?: (analysis: KATNISSResponse) => void
}

export function SessionAnalysis({ athleteName = 'Deportista', onComplete }: SessionAnalysisProps) {
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
  const [result, setResult] = useState<KATNISSResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const emotionEmojis = {
    happy: '😊',
    neutral: '😐',
    tired: '😴'
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

      // Guardar en IndexedDB
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
    <div className={styles.container}>
      {step === 'input' && (
        <form onSubmit={handleSubmit} className={styles.form}>
          <h2>¿Cómo te fue en la sesión?</h2>

          {/* Duration */}
          <div className={styles.formGroup}>
            <label>Duración (minutos)</label>
            <div className={styles.slider}>
              <input
                type="range"
                min="5"
                max="120"
                step="5"
                value={formData.duration}
                onChange={(e) =>
                  setFormData({ ...formData, duration: Number(e.target.value) })
                }
              />
              <span className={styles.value}>{formData.duration} min</span>
            </div>
          </div>

          {/* RPE */}
          <div className={styles.formGroup}>
            <label>¿Cuánto esfuerzo hiciste? (1-10)</label>
            <div className={styles.rpeButtons}>
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                <button
                  key={num}
                  type="button"
                  className={`${styles.rpeBtn} ${
                    formData.rpe === num ? styles.selected : ''
                  }`}
                  onClick={() => setFormData({ ...formData, rpe: num })}
                >
                  {num}
                </button>
              ))}
            </div>
          </div>

          {/* Emotional Check-in */}
          <div className={styles.formGroup}>
            <label>¿Cómo te sientes ahora?</label>
            <div className={styles.emotionButtons}>
              {(['happy', 'neutral', 'tired'] as const).map((emotion) => (
                <button
                  key={emotion}
                  type="button"
                  className={`${styles.emotionBtn} ${
                    formData.emotionalCheckIn === emotion ? styles.selected : ''
                  }`}
                  onClick={() =>
                    setFormData({ ...formData, emotionalCheckIn: emotion })
                  }
                >
                  <span className={styles.emoji}>
                    {emotionEmojis[emotion]}
                  </span>
                  <span className={styles.label}>
                    {emotion === 'happy'
                      ? 'Feliz'
                      : emotion === 'neutral'
                        ? 'Normal'
                        : 'Cansado'}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Notes */}
          <div className={styles.formGroup}>
            <label>Notas (opcional)</label>
            <textarea
              value={formData.notes}
              onChange={(e) =>
                setFormData({ ...formData, notes: e.target.value })
              }
              placeholder="¿Algo más que quieras contar?"
              rows={3}
            />
          </div>

          {error && <div className={styles.error}>{error}</div>}

          <button type="submit" className={styles.submitBtn}>
            Obtener Feedback de KATNISS
          </button>
        </form>
      )}

      {step === 'loading' && (
        <div className={styles.loading}>
          <div className={styles.spinner}></div>
          <p>KATNISS analizando tu sesión...</p>
        </div>
      )}

      {step === 'result' && result && (
        <div className={styles.result}>
          <h2>✨ Feedback de KATNISS ✨</h2>

          <div className={styles.resultCard}>
            <div className={styles.motivationSection}>
              <h3>Motivación</h3>
              <p className={styles.motivation}>{result.motivation}</p>
            </div>

            <div className={styles.suggestionSection}>
              <h3>Próxima Sesión</h3>
              <p className={styles.suggestion}>
                💡 {result.nextSuggestion}
              </p>
              <p className={styles.dayRecommended}>
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
            className={styles.continueBtn}
          >
            Otra Sesión
          </button>
        </div>
      )}
    </div>
  )
}
