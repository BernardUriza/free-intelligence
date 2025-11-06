import { useState, useMemo } from 'react'
import styles from '../styles/t21-resources.module.css'
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
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>🧬 T21 - Recursos y Apoyo</h1>
        <p>Información y herramientas para el Síndrome de Down</p>
      </div>

      {/* Categories */}
      <div className={styles.categories}>
        {CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            className={`${styles.categoryBtn} ${
              selectedCategory === cat.id ? styles.active : ''
            }`}
            onClick={() => setSelectedCategory(cat.id)}
          >
            {cat.icon} {cat.label}
          </button>
        ))}
      </div>

      {/* Resources Grid */}
      {loading ? (
        <div className={styles.loading}>
          <p>📚 Cargando recursos...</p>
        </div>
      ) : filteredResources.length === 0 ? (
        <div className={styles.empty}>
          <p>📭 No hay recursos disponibles</p>
        </div>
      ) : (
        <div className={styles.grid}>
          {filteredResources.map((resource) => (
            <div key={resource.id} className={styles.card}>
              <div className={styles.cardIcon}>{resource.icon}</div>

              <h3>{resource.title}</h3>
              <p className={styles.description}>{resource.description}</p>

              <div className={styles.categoryTag}>{resource.category}</div>

              {resource.url && (
                <a href={resource.url} target="_blank" rel="noopener noreferrer" className={styles.btn}>
                  👁️ Ver Recurso
                </a>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Support Section */}
      <div className={styles.support}>
        <h2>💙 ¿Necesitas Ayuda?</h2>
        <div className={styles.supportCards}>
          <div className={styles.supportCard}>
            <h3>📞 Línea de Apoyo</h3>
            <p>Llama al: 1-800-T21-HELP</p>
            <p className={styles.small}>Disponible 24/7</p>
          </div>

          <div className={styles.supportCard}>
            <h3>💬 Chat en Vivo</h3>
            <p>Habla con un especialista</p>
            <button className={styles.chatBtn}>Iniciar Chat</button>
          </div>

          <div className={styles.supportCard}>
            <h3>📧 Email</h3>
            <p>apoyo@fi-stride.com</p>
            <p className={styles.small}>Respuesta en 24h</p>
          </div>
        </div>
      </div>
    </div>
  )
}
