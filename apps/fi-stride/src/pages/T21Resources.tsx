import { useState, useMemo } from 'react'
import { useDataFetch } from '../hooks/useDataFetch'
import { T21ResourcesResponse } from '../types/api'

// Categories constant - moved out of render to prevent recreation
const CATEGORIES = [
  { id: 'all', label: 'Todas', icon: '🌟' },
  { id: 'guide', label: 'Guías', icon: '📖' },
  { id: 'video', label: 'Vídeos', icon: '🎬' },
  { id: 'article', label: 'Artículos', icon: '📄' },
  { id: 'tool', label: 'Herramientas', icon: '🛠️' },
]

export function T21Resources() {
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  const { data: response, loading } = useDataFetch<T21ResourcesResponse>({
    url: '/api/t21/resources'
  })

  const resources = response?.resources || []

  const filteredResources = useMemo(
    () =>
      selectedCategory === 'all'
        ? resources
        : resources.filter((r) => r.category === selectedCategory),
    [resources, selectedCategory]
  )

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-green-600 to-blue-600 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <h1 className="text-4xl font-bold">🧬 T21 - Recursos y Apoyo</h1>
          <p className="text-green-100 mt-2">Información y herramientas para el Síndrome de Down</p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Categories */}
        <div className="flex gap-2 flex-wrap">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              type="button"
              className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 whitespace-nowrap ${
                selectedCategory === cat.id
                  ? 'bg-green-600 text-white ring-2 ring-green-400'
                  : 'bg-white text-gray-900 border border-gray-300 hover:bg-gray-100'
              }`}
            >
              {cat.icon} {cat.label}
            </button>
          ))}
        </div>

        {/* Resources Grid */}
        {loading ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <p className="text-lg font-semibold text-gray-900">📚 Cargando recursos...</p>
          </div>
        ) : filteredResources.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <p className="text-3xl mb-2">📭</p>
            <p className="text-lg text-gray-600">No hay recursos disponibles</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredResources.map((resource) => (
              <div key={resource.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow flex flex-col">
                <div className="text-4xl mb-4">{resource.icon}</div>

                <h3 className="text-lg font-bold text-gray-900 mb-2">{resource.title}</h3>
                <p className="text-gray-600 text-sm mb-4 flex-grow">{resource.description}</p>

                <div className="mb-4">
                  <span className="inline-block px-3 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded-full">
                    {resource.category}
                  </span>
                </div>

                {resource.url && (
                  <a
                    href={resource.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium text-center text-sm"
                  >
                    👁️ Ver Recurso
                  </a>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Support Section */}
        <div className="mt-12 pt-8 border-t border-gray-200 space-y-6">
          <h2 className="text-3xl font-bold text-gray-900">💙 ¿Necesitas Ayuda?</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div key="support-phone" className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-3">📞 Línea de Apoyo</h3>
              <p className="text-gray-700 font-semibold mb-1">Llama al: 1-800-T21-HELP</p>
              <p className="text-sm text-gray-500">Disponible 24/7</p>
            </div>

            <div key="support-chat" className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-3">💬 Chat en Vivo</h3>
              <p className="text-gray-700 mb-4">Habla con un especialista</p>
              <button className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm">
                Iniciar Chat
              </button>
            </div>

            <div key="support-email" className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-3">📧 Email</h3>
              <p className="text-gray-700 font-semibold mb-1">apoyo@fi-stride.com</p>
              <p className="text-sm text-gray-500">Respuesta en 24h</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
