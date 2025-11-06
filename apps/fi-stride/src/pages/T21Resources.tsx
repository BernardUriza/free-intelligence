import { useState, useEffect } from 'react'
import styles from '../styles/t21-resources.module.css'

interface Resource {
  id: string
  title: string
  description: string
  category: 'guide' | 'video' | 'article' | 'tool'
  url?: string
  icon: string
}

export function T21Resources() {
  const [resources, setResources] = useState<Resource[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  useEffect(() => {
    const fetchResources = async () => {
      try {
        setLoading(true)
        const response = await fetch('/api/t21/resources')
        const data = await response.json()
        setResources(data.resources || [])
      } catch (err) {
        console.error('Error loading resources:', err)
        // Use default resources on error
        setResources(defaultResources)
      } finally {
        setLoading(false)
      }
    }

    fetchResources()
  }, [])

  const filteredResources =
    selectedCategory === 'all'
      ? resources
      : resources.filter((r) => r.category === selectedCategory)

  const categories = [
    { id: 'all', label: 'Todas', icon: '🌟' },
    { id: 'guide', label: 'Guías', icon: '📖' },
    { id: 'video', label: 'Vídeos', icon: '🎬' },
    { id: 'article', label: 'Artículos', icon: '📄' },
    { id: 'tool', label: 'Herramientas', icon: '🛠️' },
  ]

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>🧬 T21 - Recursos y Apoyo</h1>
        <p>Información y herramientas para el Síndrome de Down</p>
      </div>

      {/* Categories */}
      <div className={styles.categories}>
        {categories.map((cat) => (
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

// Default resources (fallback)
const defaultResources: Resource[] = [
  {
    id: '1',
    title: 'Guía de Inclusión Deportiva',
    description: 'Cómo incluir atletas con T21 en deportes',
    category: 'guide',
    icon: '📖',
    url: '#',
  },
  {
    id: '2',
    title: 'Vídeo: Ejercicios Seguros',
    description: 'Los 5 ejercicios más seguros para empezar',
    category: 'video',
    icon: '🎬',
    url: '#',
  },
  {
    id: '3',
    title: 'Artículo: Nutrición y T21',
    description: 'Información sobre necesidades nutricionales',
    category: 'article',
    icon: '📄',
    url: '#',
  },
]
