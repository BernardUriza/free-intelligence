import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { SessionAnalysis } from './SessionAnalysis'
import styles from '../styles/athlete-flow.module.css'

type Step = 'consent' | 'permissions' | 'profile' | 'ready' | 'session-demo'

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

  const isConsentComplete = consents.privacy && consents.encryption && consents.dataProcessing
  const isPermissionsComplete = permissions.camera || permissions.microphone

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <h1>FI-Stride</h1>
        <p>Bienvenido, {user?.name}! 🏃</p>
        <button onClick={logout} className={styles.logoutBtn}>
          Cerrar sesión
        </button>
      </header>

      {/* Progress Bar */}
      <div className={styles.progressContainer}>
        <div className={styles.progressSteps}>
          <div className={`${styles.step} ${currentStep === 'consent' ? styles.active : ''}`}>
            Privacidad
          </div>
          <div className={`${styles.step} ${currentStep === 'permissions' ? styles.active : ''}`}>
            Permisos
          </div>
          <div className={`${styles.step} ${currentStep === 'profile' ? styles.active : ''}`}>
            Perfil
          </div>
          <div className={`${styles.step} ${currentStep === 'ready' ? styles.active : ''}`}>
            Listo
          </div>
        </div>
        <div
          className={styles.progressBar}
          style={{
            width: `${((['consent', 'permissions', 'profile', 'ready'].indexOf(currentStep) + 1) / 4) * 100}%`
          }}
        />
      </div>

      {/* Content */}
      <main className={styles.main}>
        {/* Privacy Consent Step */}
        {currentStep === 'consent' && (
          <section className={styles.step_content}>
            <h2>Privacidad y Consentimiento</h2>
            <p className={styles.subtitle}>
              Necesitamos tu consentimiento para usar tus datos de forma segura
            </p>

            <div className={styles.consentCard}>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={consents.privacy}
                  onChange={() => handleConsentChange('privacy')}
                />
                <span>
                  <strong>Política de Privacidad</strong>
                  <br />
                  Acepto que mis datos se usen solo para mejorar mi entrenamiento
                </span>
              </label>
            </div>

            <div className={styles.consentCard}>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={consents.encryption}
                  onChange={() => handleConsentChange('encryption')}
                />
                <span>
                  <strong>Encriptación</strong>
                  <br />
                  Entiendo que mis datos están protegidos con cifrado de extremo a extremo
                </span>
              </label>
            </div>

            <div className={styles.consentCard}>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={consents.dataProcessing}
                  onChange={() => handleConsentChange('dataProcessing')}
                />
                <span>
                  <strong>Procesamiento de Datos</strong>
                  <br />
                  Acepto que se analicen mis sesiones para mejorar el entrenamiento
                </span>
              </label>
            </div>
          </section>
        )}

        {/* Permissions Step */}
        {currentStep === 'permissions' && (
          <section className={styles.step_content}>
            <h2>Permisos de Dispositivo</h2>
            <p className={styles.subtitle}>
              Selecciona qué sensores quieres usar durante tus sesiones
            </p>

            <div className={styles.permissionCard}>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={permissions.camera}
                  onChange={() => handlePermissionChange('camera')}
                />
                <span>
                  <strong>📷 Cámara</strong>
                  <br />
                  Para verificar tu postura y movimiento
                </span>
              </label>
            </div>

            <div className={styles.permissionCard}>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={permissions.microphone}
                  onChange={() => handlePermissionChange('microphone')}
                />
                <span>
                  <strong>🎤 Micrófono</strong>
                  <br />
                  Para registrar comandos de voz (opcional)
                </span>
              </label>
            </div>

            <div className={styles.permissionCard}>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={permissions.location}
                  onChange={() => handlePermissionChange('location')}
                  disabled
                />
                <span>
                  <strong>📍 Ubicación</strong>
                  <br />
                  Próximamente en actualizaciones futuras
                </span>
              </label>
            </div>
          </section>
        )}

        {/* Profile Step */}
        {currentStep === 'profile' && (
          <section className={styles.step_content}>
            <h2>Tu Perfil</h2>
            <p className={styles.subtitle}>Información de tu cuenta</p>

            <div className={styles.profileInfo}>
              <div className={styles.formGroup}>
                <label>Nombre</label>
                <input type="text" defaultValue={user?.name} disabled />
              </div>

              <div className={styles.formGroup}>
                <label>Correo</label>
                <input type="email" defaultValue={user?.email} disabled />
              </div>

              <div className={styles.formGroup}>
                <label>Rol</label>
                <input type="text" defaultValue="Deportista" disabled />
              </div>
            </div>
          </section>
        )}

        {/* Ready Step */}
        {currentStep === 'ready' && (
          <section className={styles.step_content}>
            <div className={styles.readyCard}>
              <h2>¡Listo para entrenar! 🎉</h2>
              <p>
                Tu perfil está completamente configurado. Ahora puedes comenzar tu primer entrenamiento
                personalizado con FI-Stride.
              </p>
              <ul className={styles.checklist}>
                <li>✅ Privacidad confirmada</li>
                <li>✅ Permisos configurados</li>
                <li>✅ Perfil completado</li>
              </ul>
            </div>
          </section>
        )}

        {currentStep === 'session-demo' && (
          <section className={styles.step_content}>
            <SessionAnalysis athleteName={user?.name} />
          </section>
        )}
      </main>

      {/* Navigation Buttons */}
      <div className={styles.footer}>
        {currentStep !== 'consent' && (
          <button onClick={handlePrevStep} className={styles.secondaryBtn}>
            ← Atrás
          </button>
        )}
        {currentStep !== 'ready' && (
          <button
            onClick={handleNextStep}
            disabled={
              (currentStep === 'consent' && !isConsentComplete) ||
              (currentStep === 'permissions' && !isPermissionsComplete)
            }
            className={styles.primaryBtn}
          >
            Siguiente →
          </button>
        )}
        {currentStep === 'ready' && (
          <button
            onClick={() => setCurrentStep('session-demo')}
            className={styles.primaryBtn}
          >
            Comenzar Entrenamiento 💪
          </button>
        )}

        {currentStep === 'session-demo' && (
          <button
            onClick={() => {
              setCurrentStep('consent')
              // Reset flow
            }}
            className={styles.secondaryBtn}
          >
            ← Volver al inicio
          </button>
        )}
      </div>
    </div>
  )
}
