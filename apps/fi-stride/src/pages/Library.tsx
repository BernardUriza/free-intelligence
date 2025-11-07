import { useState, useMemo } from 'react'
import { useDataFetch } from '../hooks/useDataFetch'
import { FilterBar, FilterOption } from '../components/FilterBar'
import { ConsultationsResponse } from '../types/api'

const LIBRARY_FILTERS: FilterOption[] = [
  { id: 'all', label: 'Todas' },
  { id: 'recent', label: 'Recientes' },
  { id: 'archived', label: 'Archivadas' }
]

export function Library() {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'recent' | 'archived'>('all')

  const { data: response, loading, error } = useDataFetch<ConsultationsResponse>({
    url: '/api/consultations',
    headers: {
      Authorization: `Bearer ${localStorage.getItem('fi-stride-auth-token') || ''}`,
    }
  })

  const consultations = response?.consultations || []

  const filteredConsultations = useMemo(() => {
    const now = new Date()
    return consultations.filter((c) => {
      const matchesSearch = c.consultationId.toLowerCase().includes(search.toLowerCase())
      const consultDate = new Date(c.createdAt)
      const daysOld = (now.getTime() - consultDate.getTime()) / (1000 * 60 * 60 * 24)

      switch (filter) {
        case 'recent':
          return matchesSearch && daysOld <= 7
        case 'archived':
          return matchesSearch && daysOld > 30
        default:
          return matchesSearch
      }
    })
  }, [consultations, search, filter])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 flex items-center justify-center">
          <div className="text-center">
            <p className="text-2xl">📚 Cargando biblioteca...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <h1 className="text-4xl font-bold">📚 Mi Biblioteca</h1>
          <p className="text-blue-100 mt-2">Tus sesiones guardadas y consultas</p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search & Filter */}
        <FilterBar
          searchPlaceholder="🔍 Buscar sesión..."
          searchValue={search}
          onSearchChange={setSearch}
          filters={LIBRARY_FILTERS}
          activeFilter={filter}
          onFilterChange={(id) => setFilter(id as 'all' | 'recent' | 'archived')}
        />

        {/* Error */}
        {error && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {/* Consultations Grid */}
        {filteredConsultations.length === 0 ? (
          <div className="mt-12 text-center">
            <p className="text-3xl mb-4">📭</p>
            <p className="text-xl text-gray-600">No hay consultas para mostrar</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
            {filteredConsultations.map((consultation) => (
              <div key={consultation.id} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
                {/* Card Header */}
                <div className="px-6 py-4 bg-gradient-to-r from-blue-50 to-purple-50 border-b border-gray-200">
                  <div className="flex justify-between items-start gap-4">
                    <h3 className="font-bold text-gray-900 text-lg">{consultation.consultationId}</h3>
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold bg-blue-100 text-blue-800 whitespace-nowrap">
                      {consultation.eventCount} eventos
                    </span>
                  </div>
                </div>

                {/* Card Body */}
                <div className="px-6 py-4 space-y-2">
                  <p className="text-gray-700">
                    <strong className="text-gray-900">Fecha:</strong>{' '}
                    {new Date(consultation.createdAt).toLocaleDateString('es-ES')}
                  </p>
                  {consultation.updatedAt && (
                    <p className="text-gray-700">
                      <strong className="text-gray-900">Actualizado:</strong>{' '}
                      {new Date(consultation.updatedAt).toLocaleDateString('es-ES')}
                    </p>
                  )}
                </div>

                {/* Card Footer */}
                <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex gap-3">
                  <button className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm">
                    👁️ Ver
                  </button>
                  <button className="flex-1 px-4 py-2 bg-gray-200 text-gray-900 rounded-lg hover:bg-gray-300 transition-colors font-medium text-sm">
                    📤 Exportar
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
