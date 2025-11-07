import { useState, useEffect } from 'react'
import styles from '../styles/privacy.module.css'
import { useAuthStore } from '../store/authStore'

export function Privacy() {
  const [activeSection, setActiveSection] = useState<string | null>(null)
  const [cacheStats, setCacheStats] = useState<{ exerciseCount: number; estimatedSize: string }>({
    exerciseCount: 0,
    estimatedSize: '0MB',
  })
  const [isClearing, setIsClearing] = useState(false)
  const [showConfirmClear, setShowConfirmClear] = useState(false)
  const user = useAuthStore((state) => state.user)

  // Load cache stats on mount
  useEffect(() => {
    const loadCacheStats = async () => {
      try {
        // Try to get exerciseStorage stats if available
        const { exerciseStorage } = await import('../services/exerciseStorage')
        const stats = await exerciseStorage.getStorageStats()
        setCacheStats(stats)
      } catch (error) {
        console.error('Failed to load cache stats:', error)
      }
    }
    loadCacheStats()
  }, [])

  /**
   * Clear all cached data (exercises, videos, metadata)
   */
  const handleClearCache = async () => {
    setIsClearing(true)
    try {
      const { exerciseStorage } = await import('../services/exerciseStorage')
      await exerciseStorage.clearAllData()
      setCacheStats({ exerciseCount: 0, estimatedSize: '0MB' })
      setShowConfirmClear(false)
      // Optionally show success message
      alert('✅ Caché eliminado correctamente')
    } catch (error) {
      console.error('Failed to clear cache:', error)
      alert('❌ Error al limpiar caché')
    } finally {
      setIsClearing(false)
    }
  }

  /**
   * Download user data as JSON
   */
  const handleDownloadData = async () => {
    try {
      const userData = {
        user: user,
        exportedAt: new Date().toISOString(),
        dataVersion: '1.0',
      }

      // Try to include cached exercises if available
      try {
        const { exerciseStorage } = await import('../services/exerciseStorage')
        const exercises = await exerciseStorage.getAllExercises()
        userData.exercises = exercises
      } catch {
        // Continue without exercises if storage not available
      }

      const dataStr = JSON.stringify(userData, null, 2)
      const dataBlob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(dataBlob)
      const link = document.createElement('a')
      link.href = url
      link.download = `fi-stride-personal-data-${Date.now()}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to download data:', error)
      alert('❌ Error al descargar datos')
    }
  }

  /**
   * Revoke all permissions and logout
   */
  const handleRevokePermissions = () => {
    const confirmed = window.confirm(
      '⚠️ Esto revocará todos los permisos y cerrará tu sesión. ¿Continuar?'
    )
    if (confirmed) {
      // Clear localStorage and logout
      localStorage.removeItem('fi-stride-user')
      localStorage.removeItem('fi-stride-auth-token')
      const { logout } = useAuthStore.getState()
      logout()
      window.location.href = '/'
    }
  }

  const sections = [
    {
      id: 'privacy-policy',
      title: '🔒 Política de Privacidad',
      content: `
Nosotros en FI-Stride respetamos tu privacidad.

**Qué datos recopilamos:**
- Tu nombre y correo electrónico
- Información sobre tus sesiones de entrenamiento
- Datos de tu progreso en ejercicios

**Cómo usamos tus datos:**
- Para mejorar tu experiencia
- Para personalizar recomendaciones
- Para análisis anónimo de uso

**Tus derechos:**
- Puedes acceder a tus datos en cualquier momento
- Puedes solicitar la eliminación de tus datos
- Puedes exportar tus datos

**Cómo contactarnos:**
Email: privacidad@fi-stride.com
      `,
    },
    {
      id: 'data-security',
      title: '🛡️ Seguridad de Datos',
      content: `
Protegemos tu información con:

**Encriptación:**
- Todos los datos se transmiten con SSL/TLS
- Los datos en reposo están encriptados

**Acceso:**
- Solo tú puedes ver tus datos
- Los profesionales ven solo lo que autorizas

**Copias de seguridad:**
- Realizamos copias automáticas diarias
- Mantenemos múltiples copias en ubicaciones seguras

**Cumplimiento:**
- Cumplimos con GDPR y leyes locales
- Auditorías de seguridad regulares
      `,
    },
    {
      id: 'data-deletion',
      title: '🗑️ Eliminar Mis Datos',
      content: `
Entendemos que quizás desees eliminar tu cuenta y datos.

**Proceso de eliminación:**
1. Solicita la eliminación desde tu perfil
2. Te pediremos confirmar tu contraseña
3. Tus datos se eliminarán en 30 días (período de gracia)
4. Recibirás un email de confirmación

**Qué se elimina:**
- Tu perfil y cuenta
- Todas tus sesiones de entrenamiento
- Tus datos personales

**Qué NO se elimina:**
- Datos anónimos usados para mejorar la app
- Copias en archivos históricamente necesarios

**Contacto:**
Si tienes dudas: derechos@fi-stride.com
      `,
    },
  ]

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>🔐 Privacidad y Seguridad</h1>
        <p>Tu información está segura con nosotros</p>
      </div>

      <div className={styles.content}>
        {sections.map((section) => (
          <div key={section.id} className={styles.section}>
            <button
              className={styles.sectionHeader}
              onClick={() =>
                setActiveSection(activeSection === section.id ? null : section.id)
              }
            >
              <span>{section.title}</span>
              <span className={styles.toggle}>
                {activeSection === section.id ? '▼' : '▶'}
              </span>
            </button>

            {activeSection === section.id && (
              <div className={styles.sectionBody}>
                {section.content.split('\n').map((line, idx) => (
                  <p key={idx} className={line.startsWith('**') ? styles.bold : ''}>
                    {line.replace(/\*\*/g, '')}
                  </p>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Cache Management */}
      <div className={styles.dataControl}>
        <h2>💾 Gestión de Caché</h2>
        <div className={styles.cacheInfo}>
          <div className={styles.statItem}>
            <span className={styles.statLabel}>📦 Ejercicios descargados:</span>
            <span className={styles.statValue}>{cacheStats.exerciseCount}</span>
          </div>
          <div className={styles.statItem}>
            <span className={styles.statLabel}>📊 Espacio usado:</span>
            <span className={styles.statValue}>{cacheStats.estimatedSize}</span>
          </div>
        </div>

        {showConfirmClear ? (
          <div className={styles.confirmBox}>
            <p>⚠️ ¿Estás seguro? Se eliminarán todos los ejercicios descargados.</p>
            <div className={styles.buttonGroup}>
              <button
                className={styles.dangerBtn}
                onClick={handleClearCache}
                disabled={isClearing}
              >
                {isClearing ? '⏳ Limpiando...' : '🗑️ Eliminar Caché'}
              </button>
              <button className={styles.cancelBtn} onClick={() => setShowConfirmClear(false)}>
                Cancelar
              </button>
            </div>
          </div>
        ) : (
          <button
            className={styles.actionBtn}
            onClick={() => setShowConfirmClear(true)}
            disabled={cacheStats.exerciseCount === 0}
          >
            🗑️ Limpiar Caché Local
          </button>
        )}
      </div>

      {/* Data Control */}
      <div className={styles.dataControl}>
        <h2>📥 Control de Datos</h2>
        <p>Descarga o revoca tu información personal</p>

        <div className={styles.buttonGroup}>
          <button className={styles.actionBtn} onClick={handleDownloadData}>
            📥 Descargar Mis Datos (JSON)
          </button>
          <button className={styles.dangerBtn} onClick={handleRevokePermissions}>
            🚫 Revocar Permisos y Cerrar Sesión
          </button>
        </div>
      </div>

      {/* Consent Form */}
      <div className={styles.consent}>
        <h2>✅ Acepto los términos</h2>
        <div className={styles.checkboxGroup}>
          <label className={styles.checkboxLabel}>
            <input type="checkbox" defaultChecked />
            <span>He leído la política de privacidad</span>
          </label>
          <label className={styles.checkboxLabel}>
            <input type="checkbox" defaultChecked />
            <span>Autorizo el procesamiento de mis datos</span>
          </label>
          <label className={styles.checkboxLabel}>
            <input type="checkbox" />
            <span>Autorizo el envío de recomendaciones</span>
          </label>
        </div>

        <button className={styles.saveBtn}>💾 Guardar Preferencias</button>
      </div>
    </div>
  )
}
