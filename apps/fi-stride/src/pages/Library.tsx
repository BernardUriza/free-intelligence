import { useState, useEffect } from 'react'
import styles from '../styles/library.module.css'

interface Consultation {
  id: string
  consultationId: string
  eventCount: number
  createdAt: string
  updatedAt: string
}

export function Library() {
  const [consultations, setConsultations] = useState<Consultation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'recent' | 'archived'>('all')

  useEffect(() => {
    const fetchConsultations = async () => {
      try {
        setLoading(true)
        const response = await fetch('/api/consultations', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('fi-stride-auth-token')}`,
          },
        })

        if (!response.ok) throw new Error('Failed to fetch consultations')

        const data = await response.json()
        setConsultations(data.consultations || [])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error loading library')
      } finally {
        setLoading(false)
      }
    }

    fetchConsultations()
  }, [])

  const filteredConsultations = consultations.filter((c) => {
    const matchesSearch = c.consultationId.toLowerCase().includes(search.toLowerCase())
    const now = new Date()
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
      <div className={styles.controls}>
        <input
          type="text"
          placeholder="🔍 Buscar sesión..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className={styles.searchInput}
        />

        <div className={styles.filterButtons}>
          <button
            className={`${styles.filterBtn} ${filter === 'all' ? styles.active : ''}`}
            onClick={() => setFilter('all')}
          >
            Todas
          </button>
          <button
            className={`${styles.filterBtn} ${filter === 'recent' ? styles.active : ''}`}
            onClick={() => setFilter('recent')}
          >
            Recientes
          </button>
          <button
            className={`${styles.filterBtn} ${filter === 'archived' ? styles.active : ''}`}
            onClick={() => setFilter('archived')}
          >
            Archivadas
          </button>
        </div>
      </div>

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
