/**
 * Session Designer Component (Coach)
 * Allows coaches to create, edit, clone and publish training sessions
 *
 * Features:
 * - Predefined session blocks (warmup, movement, breathing, cool-down)
 * - Duration and description per block
 * - Safety tips that display as contextual modals during athlete session
 * - Publish to athlete with date scheduling
 * - Session history with clone functionality
 */

import { useState } from 'react'
import styles from '../styles/dashboard.module.css'

interface SessionBlock {
  id: string
  type: 'warmup' | 'movement' | 'breathing' | 'cooldown'
  duration: number
  description: string
}

interface SafetyTip {
  id: string
  blockId: string
  title: string
  content: string
}

interface Session {
  id: string
  name: string
  blocks: SessionBlock[]
  safetyTips: SafetyTip[]
  createdAt: Date
  publishedTo?: {
    athleteId: string
    athleteName: string
    publishedAt: Date
  }
}

export function SessionDesigner() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [editingSession, setEditingSession] = useState<Session | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [showHistory, setShowHistory] = useState(false)

  // Block type definitions
  const blockTypes = [
    { type: 'warmup', label: '🔥 Calentamiento', emoji: '🔥', color: '#ed8936' },
    { type: 'movement', label: '💪 Movimiento', emoji: '💪', color: '#48bb78' },
    { type: 'breathing', label: '🌬️ Respiración', emoji: '🌬️', color: '#667eea' },
    { type: 'cooldown', label: '❄️ Enfriamiento', emoji: '❄️', color: '#9f7aea' },
  ] as const

  // Create new session
  const createNewSession = () => {
    const newSession: Session = {
      id: `session_${Date.now()}`,
      name: 'Nueva Sesión',
      blocks: [],
      safetyTips: [],
      createdAt: new Date(),
    }
    setEditingSession(newSession)
    setIsModalOpen(true)
  }

  // Clone session
  const cloneSession = (session: Session) => {
    const clonedSession: Session = {
      id: `session_${Date.now()}`,
      name: `${session.name} (Copia)`,
      blocks: session.blocks.map((b) => ({ ...b, id: `${b.id}_${Date.now()}` })),
      safetyTips: session.safetyTips.map((t) => ({ ...t, id: `${t.id}_${Date.now()}` })),
      createdAt: new Date(),
    }
    setEditingSession(clonedSession)
    setIsModalOpen(true)
  }

  // Add block to session
  const addBlock = () => {
    if (!editingSession) return
    const newBlock: SessionBlock = {
      id: `block_${Date.now()}`,
      type: 'movement',
      duration: 10,
      description: '',
    }
    setEditingSession({
      ...editingSession,
      blocks: [...editingSession.blocks, newBlock],
    })
  }

  // Update block
  const updateBlock = (blockId: string, updates: Partial<SessionBlock>) => {
    if (!editingSession) return
    setEditingSession({
      ...editingSession,
      blocks: editingSession.blocks.map((b) =>
        b.id === blockId ? { ...b, ...updates } : b
      ),
    })
  }

  // Remove block
  const removeBlock = (blockId: string) => {
    if (!editingSession) return
    setEditingSession({
      ...editingSession,
      blocks: editingSession.blocks.filter((b) => b.id !== blockId),
      safetyTips: editingSession.safetyTips.filter((t) => t.blockId !== blockId),
    })
  }

  // Add safety tip
  const addSafetyTip = (blockId: string) => {
    if (!editingSession) return
    const newTip: SafetyTip = {
      id: `tip_${Date.now()}`,
      blockId,
      title: 'Nuevo Consejo',
      content: '',
    }
    setEditingSession({
      ...editingSession,
      safetyTips: [...editingSession.safetyTips, newTip],
    })
  }

  // Update safety tip
  const updateSafetyTip = (tipId: string, updates: Partial<SafetyTip>) => {
    if (!editingSession) return
    setEditingSession({
      ...editingSession,
      safetyTips: editingSession.safetyTips.map((t) =>
        t.id === tipId ? { ...t, ...updates } : t
      ),
    })
  }

  // Save session
  const saveSession = () => {
    if (!editingSession) return
    if (editingSession.blocks.length === 0) {
      alert('⚠️ Agrega al menos un bloque a la sesión')
      return
    }

    const existingIndex = sessions.findIndex((s) => s.id === editingSession.id)
    if (existingIndex >= 0) {
      setSessions(sessions.map((s, i) => (i === existingIndex ? editingSession : s)))
    } else {
      setSessions([...sessions, editingSession])
    }

    setEditingSession(null)
    setIsModalOpen(false)
  }

  // Publish session
  const publishSession = (sessionId: string) => {
    // Mock: In real app, this would send to backend
    const sessionIndex = sessions.findIndex((s) => s.id === sessionId)
    if (sessionIndex >= 0) {
      const updatedSession = sessions[sessionIndex]
      updatedSession.publishedTo = {
        athleteId: 'athlete_1',
        athleteName: 'Juan García',
        publishedAt: new Date(),
      }
      setSessions([...sessions.slice(0, sessionIndex), updatedSession, ...sessions.slice(sessionIndex + 1)])
      alert('✅ Sesión publicada a Juan García')
    }
  }

  // Calculate total duration
  const getTotalDuration = (blocks: SessionBlock[]) => {
    return blocks.reduce((sum, b) => sum + b.duration, 0)
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.headerContent}>
          <h1>📋 Diseñador de Sesiones</h1>
          <p>Crea y publica sesiones para tus deportistas</p>
        </div>
      </div>

      {/* Main Content */}
      <main className={styles.main}>
        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
          <button
            className={styles.primaryBtn}
            onClick={createNewSession}
            style={{ flex: 1 }}
          >
            ➕ Nueva Sesión
          </button>
          <button
            className={styles.primaryBtn}
            onClick={() => setShowHistory(!showHistory)}
            style={{ flex: 1 }}
          >
            📜 {showHistory ? 'Ocultar' : 'Ver'} Historial
          </button>
        </div>

        {/* Session History */}
        {showHistory && sessions.length > 0 && (
          <div className={styles.section}>
            <h2>📜 Historial de Sesiones</h2>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                gap: '1rem',
              }}
            >
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={styles.section}
                  style={{ borderLeft: '4px solid #667eea' }}
                >
                  <div style={{ marginBottom: '1rem' }}>
                    <h3 style={{ margin: '0 0 0.5rem 0' }}>{session.name}</h3>
                    <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>
                      {session.blocks.length} bloques • {getTotalDuration(session.blocks)} min
                    </p>
                  </div>

                  {session.publishedTo && (
                    <div
                      style={{
                        background: '#c6f6d5',
                        color: '#22543d',
                        padding: '0.5rem',
                        borderRadius: '0.25rem',
                        marginBottom: '1rem',
                        fontSize: '0.85rem',
                      }}
                    >
                      ✅ Publicada a {session.publishedTo.athleteName}
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                      className={styles.primaryBtn}
                      onClick={() => {
                        setEditingSession(session)
                        setIsModalOpen(true)
                      }}
                      style={{ flex: 1, padding: '0.5rem' }}
                    >
                      ✏️ Editar
                    </button>
                    <button
                      className={styles.primaryBtn}
                      onClick={() => cloneSession(session)}
                      style={{ flex: 1, padding: '0.5rem' }}
                    >
                      📋 Clonar
                    </button>
                    {!session.publishedTo && (
                      <button
                        className={styles.primaryBtn}
                        onClick={() => publishSession(session.id)}
                        style={{ flex: 1, padding: '0.5rem' }}
                      >
                        📤 Publicar
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {sessions.length === 0 && (
          <div className={styles.emptyState}>
            <p>📭 No hay sesiones creadas</p>
            <p style={{ fontSize: '0.9rem', color: '#999' }}>
              Comienza creando una nueva sesión con los bloques que necesites
            </p>
          </div>
        )}
      </main>

      {/* Editor Modal */}
      {isModalOpen && editingSession && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={() => setIsModalOpen(false)}
        >
          <div
            className={styles.section}
            style={{
              maxWidth: '700px',
              width: '90%',
              maxHeight: '90vh',
              overflow: 'auto',
              background: 'white',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h2 style={{ margin: 0 }}>Editar Sesión</h2>
              <button
                onClick={() => setIsModalOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '1.5rem',
                  cursor: 'pointer',
                }}
              >
                ✕
              </button>
            </div>

            {/* Session Name */}
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>
                Nombre de la Sesión
              </label>
              <input
                type="text"
                value={editingSession.name}
                onChange={(e) =>
                  setEditingSession({ ...editingSession, name: e.target.value })
                }
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #e0e0e0',
                  borderRadius: '0.5rem',
                  fontFamily: 'inherit',
                }}
              />
            </div>

            {/* Blocks */}
            <div style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ marginBottom: '1rem' }}>
                🎯 Bloques ({getTotalDuration(editingSession.blocks)} min)
              </h3>

              {editingSession.blocks.map((block, idx) => {
                const blockDef = blockTypes.find((b) => b.type === block.type)
                return (
                  <div
                    key={block.id}
                    style={{
                      padding: '1rem',
                      border: `1px solid ${blockDef?.color || '#e0e0e0'}`,
                      borderLeft: `4px solid ${blockDef?.color || '#e0e0e0'}`,
                      borderRadius: '0.5rem',
                      marginBottom: '1rem',
                    }}
                  >
                    <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.5rem' }}>
                      <select
                        value={block.type}
                        onChange={(e) =>
                          updateBlock(block.id, {
                            type: e.target.value as SessionBlock['type'],
                          })
                        }
                        style={{
                          flex: 1,
                          padding: '0.5rem',
                          border: '1px solid #e0e0e0',
                          borderRadius: '0.25rem',
                        }}
                      >
                        {blockTypes.map((bt) => (
                          <option key={bt.type} value={bt.type}>
                            {bt.label}
                          </option>
                        ))}
                      </select>

                      <input
                        type="number"
                        min="1"
                        max="120"
                        value={block.duration}
                        onChange={(e) =>
                          updateBlock(block.id, {
                            duration: parseInt(e.target.value),
                          })
                        }
                        placeholder="Duración (min)"
                        style={{
                          width: '120px',
                          padding: '0.5rem',
                          border: '1px solid #e0e0e0',
                          borderRadius: '0.25rem',
                        }}
                      />

                      <button
                        onClick={() => removeBlock(block.id)}
                        className={styles.primaryBtn}
                        style={{
                          background: '#f56565',
                          padding: '0.5rem 1rem',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        🗑️
                      </button>
                    </div>

                    <textarea
                      value={block.description}
                      onChange={(e) =>
                        updateBlock(block.id, { description: e.target.value })
                      }
                      placeholder="Descripción del bloque (ej: ejercicios, instrucciones)"
                      style={{
                        width: '100%',
                        padding: '0.5rem',
                        border: '1px solid #e0e0e0',
                        borderRadius: '0.25rem',
                        fontFamily: 'inherit',
                        minHeight: '60px',
                        marginBottom: '0.5rem',
                      }}
                    />

                    {/* Safety Tips for Block */}
                    <div style={{ marginTop: '0.5rem' }}>
                      <button
                        className={styles.primaryBtn}
                        onClick={() => addSafetyTip(block.id)}
                        style={{
                          fontSize: '0.85rem',
                          padding: '0.35rem 0.7rem',
                          width: '100%',
                        }}
                      >
                        ⚠️ Agregar Consejo de Seguridad
                      </button>

                      {editingSession.safetyTips
                        .filter((t) => t.blockId === block.id)
                        .map((tip) => (
                          <div
                            key={tip.id}
                            style={{
                              marginTop: '0.5rem',
                              padding: '0.5rem',
                              background: '#fffbf5',
                              border: '1px solid #feebc8',
                              borderRadius: '0.25rem',
                              fontSize: '0.85rem',
                            }}
                          >
                            <input
                              type="text"
                              value={tip.title}
                              onChange={(e) =>
                                updateSafetyTip(tip.id, { title: e.target.value })
                              }
                              placeholder="Título del consejo"
                              style={{
                                width: '100%',
                                padding: '0.35rem',
                                border: '1px solid #fdb022',
                                borderRadius: '0.2rem',
                                marginBottom: '0.35rem',
                                fontFamily: 'inherit',
                              }}
                            />
                            <textarea
                              value={tip.content}
                              onChange={(e) =>
                                updateSafetyTip(tip.id, { content: e.target.value })
                              }
                              placeholder="Contenido del consejo (aparecerá como modal durante la sesión)"
                              style={{
                                width: '100%',
                                padding: '0.35rem',
                                border: '1px solid #fdb022',
                                borderRadius: '0.2rem',
                                fontFamily: 'inherit',
                                minHeight: '45px',
                              }}
                            />
                          </div>
                        ))}
                    </div>
                  </div>
                )
              })}

              <button
                onClick={addBlock}
                className={styles.primaryBtn}
                style={{ width: '100%', marginTop: '1rem' }}
              >
                ➕ Agregar Bloque
              </button>
            </div>

            {/* Modal Actions */}
            <div style={{ display: 'flex', gap: '1rem' }}>
              <button
                onClick={saveSession}
                className={styles.primaryBtn}
                style={{ flex: 1 }}
              >
                💾 Guardar Sesión
              </button>
              <button
                onClick={() => setIsModalOpen(false)}
                className={styles.primaryBtn}
                style={{ flex: 1, background: '#cbd5e0', color: '#2d3748' }}
              >
                ✕ Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
