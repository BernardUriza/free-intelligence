import { useState, useEffect } from 'react'
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
        const { exerciseStorage } = await import('../services/exerciseStorage')
        const stats = await exerciseStorage.getStorageStats()
        setCacheStats(stats)
      } catch (error) {
        console.error('Failed to load cache stats:', error)
      }
    }
    loadCacheStats()
  }, [])

  const handleClearCache = async () => {
    setIsClearing(true)
    try {
      const { exerciseStorage } = await import('../services/exerciseStorage')
      await exerciseStorage.clearAllData()
      setCacheStats({ exerciseCount: 0, estimatedSize: '0MB' })
      setShowConfirmClear(false)
      alert('✅ Caché eliminado correctamente')
    } catch (error) {
      console.error('Failed to clear cache:', error)
      alert('❌ Error al limpiar caché')
    } finally {
      setIsClearing(false)
    }
  }

  const handleDownloadData = async () => {
    try {
      const userData = {
        user: user,
        exportedAt: new Date().toISOString(),
        dataVersion: '1.0',
      }

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

  const handleRevokePermissions = () => {
    const confirmed = window.confirm(
      '⚠️ Esto revocará todos los permisos y cerrará tu sesión. ¿Continuar?'
    )
    if (confirmed) {
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
      content: `Nosotros en FI-Stride respetamos tu privacidad.

Qué datos recopilamos:
• Tu nombre y correo electrónico
• Información sobre tus sesiones de entrenamiento
• Datos de tu progreso en ejercicios

Cómo usamos tus datos:
• Para mejorar tu experiencia
• Para personalizar recomendaciones
• Para análisis anónimo de uso

Tus derechos:
• Puedes acceder a tus datos en cualquier momento
• Puedes solicitar la eliminación de tus datos
• Puedes exportar tus datos

Contacto: privacidad@fi-stride.com`,
    },
    {
      id: 'data-security',
      title: '🛡️ Seguridad de Datos',
      content: `Protegemos tu información con:

Encriptación:
• Todos los datos se transmiten con SSL/TLS
• Los datos en reposo están encriptados

Acceso:
• Solo tú puedes ver tus datos
• Los profesionales ven solo lo que autorizas

Copias de seguridad:
• Realizamos copias automáticas diarias
• Mantenemos múltiples copias en ubicaciones seguras

Cumplimiento:
• Cumplimos con GDPR y leyes locales
• Auditorías de seguridad regulares`,
    },
    {
      id: 'data-deletion',
      title: '🗑️ Eliminar Mis Datos',
      content: `Entendemos que quizás desees eliminar tu cuenta y datos.

Proceso de eliminación:
1. Solicita la eliminación desde tu perfil
2. Te pediremos confirmar tu contraseña
3. Tus datos se eliminarán en 30 días (período de gracia)
4. Recibirás un email de confirmación

Qué se elimina:
• Tu perfil y cuenta
• Todas tus sesiones de entrenamiento
• Tus datos personales

Qué NO se elimina:
• Datos anónimos usados para mejorar la app
• Copias en archivos históricamente necesarios

Contacto: derechos@fi-stride.com`,
    },
  ]

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold mb-2">🔐 Privacidad y Seguridad</h1>
          <p className="text-lg text-blue-100">Tu información está segura con nosotros</p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Accordion Sections */}
        <div className="space-y-4 mb-12">
          {sections.map((section) => (
            <div key={section.id} className="border border-gray-200 rounded-lg overflow-hidden">
              <button
                className="w-full px-6 py-4 bg-gray-50 hover:bg-gray-100 flex items-center justify-between text-left font-semibold text-gray-900 transition-colors"
                onClick={() =>
                  setActiveSection(activeSection === section.id ? null : section.id)
                }
              >
                <span>{section.title}</span>
                <span className="text-xl">
                  {activeSection === section.id ? '▼' : '▶'}
                </span>
              </button>

              {activeSection === section.id && (
                <div className="px-6 py-4 bg-white border-t border-gray-200">
                  <div className="whitespace-pre-line text-gray-700 leading-relaxed">
                    {section.content}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Cache Management Section */}
        <div className="bg-gray-50 rounded-lg p-6 mb-8 border border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">💾 Gestión de Caché</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
            <div className="bg-white p-4 rounded border border-gray-200">
              <span className="text-gray-600">📦 Ejercicios descargados:</span>
              <span className="block text-2xl font-bold text-gray-900 mt-2">
                {cacheStats.exerciseCount}
              </span>
            </div>
            <div className="bg-white p-4 rounded border border-gray-200">
              <span className="text-gray-600">📊 Espacio usado:</span>
              <span className="block text-2xl font-bold text-gray-900 mt-2">
                {cacheStats.estimatedSize}
              </span>
            </div>
          </div>

          {showConfirmClear ? (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <p className="text-red-900 mb-4">⚠️ ¿Estás seguro? Se eliminarán todos los ejercicios descargados.</p>
              <div className="flex gap-3">
                <button
                  className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors disabled:opacity-50"
                  onClick={handleClearCache}
                  disabled={isClearing}
                >
                  {isClearing ? '⏳ Limpiando...' : '🗑️ Eliminar Caché'}
                </button>
                <button
                  className="px-4 py-2 bg-gray-300 text-gray-900 rounded hover:bg-gray-400 transition-colors"
                  onClick={() => setShowConfirmClear(false)}
                >
                  Cancelar
                </button>
              </div>
            </div>
          ) : (
            <button
              className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={() => setShowConfirmClear(true)}
              disabled={cacheStats.exerciseCount === 0}
            >
              🗑️ Limpiar Caché Local
            </button>
          )}
        </div>

        {/* Data Control Section */}
        <div className="bg-gray-50 rounded-lg p-6 mb-8 border border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">📥 Control de Datos</h2>
          <p className="text-gray-600 mb-6">Descarga o revoca tu información personal</p>

          <div className="space-y-3">
            <button
              className="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
              onClick={handleDownloadData}
            >
              📥 Descargar Mis Datos (JSON)
            </button>
            <button
              className="w-full px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
              onClick={handleRevokePermissions}
            >
              🚫 Revocar Permisos y Cerrar Sesión
            </button>
          </div>
        </div>

        {/* Consent Section */}
        <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">✅ Acepto los términos</h2>

          <div className="space-y-3 mb-6">
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" className="w-4 h-4" defaultChecked />
              <span className="text-gray-700">He leído la política de privacidad</span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" className="w-4 h-4" defaultChecked />
              <span className="text-gray-700">Autorizo el procesamiento de mis datos</span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" className="w-4 h-4" />
              <span className="text-gray-700">Autorizo el envío de recomendaciones</span>
            </label>
          </div>

          <button className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors">
            💾 Guardar Preferencias
          </button>
        </div>
      </div>
    </div>
  )
}
