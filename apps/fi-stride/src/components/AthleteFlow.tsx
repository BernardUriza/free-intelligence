import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { SessionAnalysis } from './SessionAnalysis'
import { LiveSessionCard } from './LiveSessionCard'

type Step = 'consent' | 'permissions' | 'profile' | 'ready' | 'session-ready' | 'session-live' | 'session-demo'

interface SessionResult {
  athleteId: string
  exerciseName: string
  repsCompleted: number
  sessionTime: number
  emotionalCheck: 1 | 2 | 3 | 4 | 5
  timestamp: string
  heartRateAvg?: number
}

export function AthleteFlow() {
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const [currentStep, setCurrentStep] = useState<Step>('consent')
  const [consents, setConsents] = useState({
    privacy: false,
    encryption: false,
    dataProcessing: false
  })
  const [permissions, setPermissions] = useState({
    camera: false,
    microphone: false,
    location: false
  })
  const [sessionResult, setSessionResult] = useState<SessionResult | null>(null)
  const [selectedExercise, setSelectedExercise] = useState('Press de Pecho')

  const handleConsentChange = (key: keyof typeof consents) => {
    setConsents((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const handlePermissionChange = (key: keyof typeof permissions) => {
    setPermissions((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const handleNextStep = () => {
    const steps: Step[] = ['consent', 'permissions', 'profile', 'ready']
    const currentIndex = steps.indexOf(currentStep)
    if (currentIndex < steps.length - 1) {
      setCurrentStep(steps[currentIndex + 1])
    }
  }

  const handlePrevStep = () => {
    const steps: Step[] = ['consent', 'permissions', 'profile', 'ready']
    const currentIndex = steps.indexOf(currentStep)
    if (currentIndex > 0) {
      setCurrentStep(steps[currentIndex - 1])
    }
  }

  const handleStartSession = () => {
    setCurrentStep('session-ready')
  }

  const handleSessionEnd = (data: SessionResult) => {
    setSessionResult(data)
    setCurrentStep('session-demo')
  }

  const isConsentComplete = consents.privacy && consents.encryption && consents.dataProcessing
  const isPermissionsComplete = permissions.camera || permissions.microphone
  const progressPercent = ((['consent', 'permissions', 'profile', 'ready'].indexOf(currentStep) + 1) / 4) * 100

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-gradient-to-r from-green-600 to-blue-600 text-white shadow-lg p-6">
        <div className="max-w-4xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold">FI-Stride</h1>
            <p className="text-green-100">Bienvenido, {user?.name}! 🏃</p>
          </div>
          <button
            onClick={logout}
            className="px-4 py-2 bg-red-500 hover:bg-red-600 rounded-lg transition-colors text-sm font-medium"
          >
            Cerrar sesión
          </button>
        </div>
      </header>

      {/* Progress Bar */}
      <div className="bg-white border-b border-gray-200 shadow-sm p-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex justify-between mb-4">
            {['Privacidad', 'Permisos', 'Perfil', 'Listo'].map((label, idx) => (
              <div
                key={label}
                className={`flex-1 text-center text-sm font-medium ${
                  idx < ['consent', 'permissions', 'profile', 'ready'].indexOf(currentStep)
                    ? 'text-green-600'
                    : idx === ['consent', 'permissions', 'profile', 'ready'].indexOf(currentStep)
                      ? 'text-blue-600'
                      : 'text-gray-400'
                }`}
              >
                {label}
              </div>
            ))}
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
            <div
              className="bg-blue-600 h-full transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Content */}
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8">
        {/* Privacy Consent Step */}
        {currentStep === 'consent' && (
          <section className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Privacidad y Consentimiento</h2>
            <p className="text-gray-600 mb-8">
              Necesitamos tu consentimiento para usar tus datos de forma segura
            </p>

            <div className="space-y-4">
              {[
                {
                  key: 'privacy',
                  title: 'Política de Privacidad',
                  desc: 'Acepto que mis datos se usen solo para mejorar mi entrenamiento',
                },
                {
                  key: 'encryption',
                  title: 'Encriptación',
                  desc: 'Entiendo que mis datos están protegidos con cifrado de extremo a extremo',
                },
                {
                  key: 'dataProcessing',
                  title: 'Procesamiento de Datos',
                  desc: 'Acepto que se analicen mis sesiones para mejorar el entrenamiento',
                },
              ].map(({ key, title, desc }) => (
                <label
                  key={key}
                  className="flex items-start gap-4 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={(consents as any)[key]}
                    onChange={() => handleConsentChange(key as keyof typeof consents)}
                    className="mt-1 w-5 h-5 accent-blue-600"
                  />
                  <div>
                    <strong className="text-gray-900 block">{title}</strong>
                    <span className="text-gray-600 text-sm">{desc}</span>
                  </div>
                </label>
              ))}
            </div>
          </section>
        )}

        {/* Permissions Step */}
        {currentStep === 'permissions' && (
          <section className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Permisos de Dispositivo</h2>
            <p className="text-gray-600 mb-8">
              Selecciona qué sensores quieres usar durante tus sesiones
            </p>

            <div className="space-y-4">
              {[
                { key: 'camera', icon: '📷', title: 'Cámara', desc: 'Para verificar tu postura y movimiento' },
                { key: 'microphone', icon: '🎤', title: 'Micrófono', desc: 'Para registrar comandos de voz (opcional)' },
                { key: 'location', icon: '📍', title: 'Ubicación', desc: 'Próximamente en actualizaciones futuras', disabled: true },
              ].map(({ key, icon, title, desc, disabled }) => (
                <label
                  key={key}
                  className={`flex items-start gap-4 p-4 border border-gray-200 rounded-lg ${
                    !disabled ? 'hover:bg-gray-50 cursor-pointer' : 'bg-gray-50 opacity-60'
                  } transition-colors`}
                >
                  <input
                    type="checkbox"
                    checked={(permissions as any)[key]}
                    onChange={() => handlePermissionChange(key as keyof typeof permissions)}
                    disabled={disabled}
                    className="mt-1 w-5 h-5 accent-blue-600"
                  />
                  <div>
                    <strong className="text-gray-900 block">{icon} {title}</strong>
                    <span className="text-gray-600 text-sm">{desc}</span>
                  </div>
                </label>
              ))}
            </div>
          </section>
        )}

        {/* Profile Step */}
        {currentStep === 'profile' && (
          <section className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Tu Perfil</h2>
            <p className="text-gray-600 mb-8">Información de tu cuenta</p>

            <div className="space-y-4">
              {[
                { label: 'Nombre', value: user?.name },
                { label: 'Correo', value: user?.email },
                { label: 'Rol', value: 'Deportista' },
              ].map(({ label, value }) => (
                <div key={label}>
                  <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
                  <input
                    type={label === 'Correo' ? 'email' : 'text'}
                    value={value}
                    disabled
                    className="w-full px-4 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-600"
                  />
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Ready Step */}
        {currentStep === 'ready' && (
          <section className="bg-gradient-to-br from-green-50 to-blue-50 rounded-lg shadow-sm border-2 border-green-200 p-8 text-center">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">¡Listo para entrenar! 🎉</h2>
            <p className="text-gray-700 mb-8 text-lg">
              Tu perfil está completamente configurado. Ahora puedes comenzar tu primer entrenamiento
              personalizado con FI-Stride.
            </p>
            <ul className="space-y-2 text-gray-700 mb-8">
              <li className="text-lg">✅ Privacidad confirmada</li>
              <li className="text-lg">✅ Permisos configurados</li>
              <li className="text-lg">✅ Perfil completado</li>
            </ul>
          </section>
        )}

        {currentStep === 'session-ready' && (
          <section className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
            <h2 className="text-3xl font-bold text-gray-900 mb-6">Selecciona tu Ejercicio</h2>
            <p className="text-gray-600 mb-8">
              Elige el ejercicio que quieres hacer hoy
            </p>

            <div className="space-y-3 max-w-md">
              {['Press de Pecho', 'Sentadillas', 'Flexiones', 'Saltos', 'Burpees'].map((exercise) => (
                <button
                  key={exercise}
                  onClick={() => {
                    setSelectedExercise(exercise)
                    setCurrentStep('session-live')
                  }}
                  className="w-full px-6 py-4 text-xl font-bold bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  {exercise}
                </button>
              ))}
            </div>
          </section>
        )}

        {currentStep === 'session-live' && (
          <section>
            <LiveSessionCard
              athleteId={user?.id || 'athlete-unknown'}
              exerciseName={selectedExercise}
              targetReps={20}
              maxHeartRate={140}
              onSessionEnd={handleSessionEnd}
            />
          </section>
        )}

        {currentStep === 'session-demo' && (
          <section>
            <SessionAnalysis athleteName={user?.name} sessionData={sessionResult} />
          </section>
        )}
      </main>

      {/* Navigation Buttons */}
      <div className="bg-white border-t border-gray-200 px-4 py-6 shadow-lg">
        <div className="max-w-4xl mx-auto flex justify-between gap-4">
          {currentStep !== 'consent' && !['session-live', 'session-ready'].includes(currentStep) && (
            <button
              onClick={handlePrevStep}
              className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            >
              ← Atrás
            </button>
          )}
          {currentStep !== 'ready' && !['session-live', 'session-demo', 'session-ready'].includes(currentStep) && (
            <button
              onClick={handleNextStep}
              disabled={
                (currentStep === 'consent' && !isConsentComplete) ||
                (currentStep === 'permissions' && !isPermissionsComplete)
              }
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed ml-auto"
            >
              Siguiente →
            </button>
          )}
          {currentStep === 'ready' && (
            <button
              onClick={handleStartSession}
              className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium ml-auto"
            >
              Comenzar Entrenamiento 💪
            </button>
          )}

          {currentStep === 'session-ready' && (
            <button
              onClick={() => setCurrentStep('ready')}
              className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            >
              ← Atrás
            </button>
          )}

          {currentStep === 'session-demo' && (
            <button
              onClick={() => setCurrentStep('consent')}
              className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            >
              ← Volver al inicio
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
