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
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">📋 Diseñador de Sesiones</h1>
        <p className="text-gray-600 mt-2">Crea y publica sesiones para tus deportistas</p>
      </div>

      {/* Main Content */}
      <div className="space-y-6">
        {/* Action Buttons */}
        <div className="flex gap-3">
          <button
            onClick={createNewSession}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            ➕ Nueva Sesión
          </button>
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors font-medium"
          >
            📜 {showHistory ? 'Ocultar' : 'Ver'} Historial
          </button>
        </div>

        {/* Session History */}
        {showHistory && sessions.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">📜 Historial de Sesiones</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className="bg-white border-l-4 border-indigo-500 border rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="mb-4">
                    <h3 className="font-bold text-gray-900">{session.name}</h3>
                    <p className="text-sm text-gray-600">
                      {session.blocks.length} bloques • {getTotalDuration(session.blocks)} min
                    </p>
                  </div>

                  {session.publishedTo && (
                    <div className="bg-green-100 text-green-800 px-3 py-2 rounded mb-4 text-sm font-semibold">
                      ✅ Publicada a {session.publishedTo.athleteName}
                    </div>
                  )}

                  <div className="flex gap-2 flex-wrap">
                    <button
                      onClick={() => {
                        setEditingSession(session)
                        setIsModalOpen(true)
                      }}
                      className="flex-1 px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors"
                    >
                      ✏️ Editar
                    </button>
                    <button
                      onClick={() => cloneSession(session)}
                      className="flex-1 px-3 py-1.5 bg-gray-600 text-white rounded text-sm hover:bg-gray-700 transition-colors"
                    >
                      📋 Clonar
                    </button>
                    {!session.publishedTo && (
                      <button
                        onClick={() => publishSession(session.id)}
                        className="flex-1 px-3 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700 transition-colors"
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
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-8 text-center">
            <p className="text-3xl mb-2">📭</p>
            <p className="text-xl text-gray-900 font-semibold">No hay sesiones creadas</p>
            <p className="text-gray-600 mt-2">
              Comienza creando una nueva sesión con los bloques que necesites
            </p>
          </div>
        )}
      </div>

      {/* Editor Modal */}
      {isModalOpen && editingSession && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setIsModalOpen(false)}
        >
          <div
            className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Editar Sesión</h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-2xl text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>

            {/* Session Name */}
            <div className="mb-6">
              <label className="block text-sm font-semibold text-gray-900 mb-2">
                Nombre de la Sesión
              </label>
              <input
                type="text"
                value={editingSession.name}
                onChange={(e) =>
                  setEditingSession({ ...editingSession, name: e.target.value })
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none transition"
              />
            </div>

            {/* Blocks */}
            <div className="mb-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">
                🎯 Bloques ({getTotalDuration(editingSession.blocks)} min)
              </h3>

              <div className="space-y-4">
                {editingSession.blocks.map((block) => {
                  const blockDef = blockTypes.find((b) => b.type === block.type)
                  const colorMap = {
                    warmup: 'border-orange-400',
                    movement: 'border-green-400',
                    breathing: 'border-blue-400',
                    cooldown: 'border-purple-400',
                  }
                  return (
                    <div
                      key={block.id}
                      className={`p-4 border-l-4 ${colorMap[block.type] || 'border-gray-400'} border rounded-lg bg-gray-50`}
                    >
                      <div className="flex gap-3 mb-3">
                        <select
                          value={block.type}
                          onChange={(e) =>
                            updateBlock(block.id, {
                              type: e.target.value as SessionBlock['type'],
                            })
                          }
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 outline-none"
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
                          placeholder="min"
                          className="w-20 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 outline-none"
                        />

                        <button
                          onClick={() => removeBlock(block.id)}
                          className="px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                        >
                          🗑️
                        </button>
                      </div>

                      <textarea
                        value={block.description}
                        onChange={(e) =>
                          updateBlock(block.id, { description: e.target.value })
                        }
                        placeholder="Descripción (ejercicios, instrucciones)"
                        rows={3}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 outline-none mb-3"
                      />

                      {/* Safety Tips */}
                      <div className="space-y-2">
                        <button
                          onClick={() => addSafetyTip(block.id)}
                          className="w-full px-3 py-2 bg-yellow-600 text-white text-sm rounded-lg hover:bg-yellow-700 transition-colors"
                        >
                          ⚠️ Agregar Consejo de Seguridad
                        </button>

                        {editingSession.safetyTips
                          .filter((t) => t.blockId === block.id)
                          .map((tip) => (
                            <div
                              key={tip.id}
                              className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg space-y-2"
                            >
                              <input
                                type="text"
                                value={tip.title}
                                onChange={(e) =>
                                  updateSafetyTip(tip.id, { title: e.target.value })
                                }
                                placeholder="Título del consejo"
                                className="w-full px-2 py-1 border border-yellow-300 rounded text-sm focus:ring-2 focus:ring-yellow-600 outline-none"
                              />
                              <textarea
                                value={tip.content}
                                onChange={(e) =>
                                  updateSafetyTip(tip.id, { content: e.target.value })
                                }
                                placeholder="Contenido (aparecerá durante la sesión)"
                                rows={2}
                                className="w-full px-2 py-1 border border-yellow-300 rounded text-sm focus:ring-2 focus:ring-yellow-600 outline-none"
                              />
                            </div>
                          ))}
                      </div>
                    </div>
                  )
                })}
              </div>

              <button
                onClick={addBlock}
                className="w-full mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                ➕ Agregar Bloque
              </button>
            </div>

            {/* Modal Actions */}
            <div className="flex gap-3">
              <button
                onClick={saveSession}
                className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
              >
                💾 Guardar Sesión
              </button>
              <button
                onClick={() => setIsModalOpen(false)}
                className="flex-1 px-4 py-2 bg-gray-300 text-gray-900 rounded-lg hover:bg-gray-400 transition-colors font-medium"
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
