import { useState, useMemo } from 'react'
import styles from '../styles/library.module.css'
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
      <div className={styles.container}>
        <div className={styles.loading}>
          <p>📚 Cargando biblioteca...</p>
        </div>
      </div>
    )
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>📚 Mi Biblioteca</h1>
        <p>Tus sesiones guardadas y consultas</p>
      </div>

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
      {error && <div className={styles.error}>{error}</div>}

      {/* Consultations Grid */}
      {filteredConsultations.length === 0 ? (
        <div className={styles.empty}>
          <p>📭 No hay consultas para mostrar</p>
        </div>
      ) : (
        <div className={styles.grid}>
          {filteredConsultations.map((consultation) => (
            <div key={consultation.id} className={styles.card}>
              <div className={styles.cardHeader}>
                <h3>{consultation.consultationId}</h3>
                <span className={styles.eventCount}>{consultation.eventCount} eventos</span>
              </div>

              <div className={styles.cardBody}>
                <p>
                  <strong>Fecha:</strong>{' '}
                  {new Date(consultation.createdAt).toLocaleDateString('es-ES')}
                </p>
                {consultation.updatedAt && (
                  <p>
                    <strong>Actualizado:</strong>{' '}
                    {new Date(consultation.updatedAt).toLocaleDateString('es-ES')}
                  </p>
                )}
              </div>

              <div className={styles.cardFooter}>
                <button className={styles.viewBtn}>
                  👁️ Ver Detalles
                </button>
                <button className={styles.exportBtn}>
                  📤 Exportar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
