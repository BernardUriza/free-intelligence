import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { SessionDesigner } from './SessionDesigner'

interface CoachStats {
  activeAthletes: number
  sessionsThisWeek: number
  avgCompletionRate: number
}

export function CoachDashboard() {
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const [activeTab, setActiveTab] = useState<'overview' | 'athletes' | 'sessions' | 'designer' | 'settings'>('overview')

  const stats: CoachStats = {
    activeAthletes: 12,
    sessionsThisWeek: 8,
    avgCompletionRate: 87,
  }

  const KPICard = ({ title, value, icon, color, suffix = '' }: { title: string; value: number; icon: string; color: string; suffix?: string }) => (
    <div className={`bg-white rounded-lg p-6 border-l-4 ${color} shadow-sm`}>
      <div className="flex justify-between items-start mb-4">
        <div>
          <p className="text-gray-600 text-sm font-medium">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{value}{suffix}</p>
        </div>
        <span className="text-4xl">{icon}</span>
      </div>
      <p className="text-xs text-gray-500 mt-4">
        {title === 'Deportistas Activos' && 'Monitoreando progreso en tiempo real'}
        {title === 'Sesiones Esta Semana' && 'Completadas y en progreso'}
        {title === 'Tasa de Completitud' && 'Promedio de equipos'}
      </p>
      {title === 'Tasa de Completitud' && (
        <div className="mt-4 w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div
            className="bg-purple-600 h-full transition-all duration-300"
            style={{ width: `${value}%` }}
          ></div>
        </div>
      )}
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-4xl font-bold">👨‍🏫 Panel de Entrenador</h1>
              <p className="text-blue-100 mt-2">Gestiona tus deportistas y sesiones</p>
            </div>
            <div className="text-right">
              <p className="text-lg">Hola, {user?.name}</p>
              <button
                onClick={logout}
                className="mt-3 px-4 py-2 bg-red-500 hover:bg-red-600 rounded-lg transition-colors text-sm font-medium"
              >
                Cerrar sesión
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex gap-1">
            {[
              { id: 'overview', label: '📊 Overview' },
              { id: 'athletes', label: '👥 Deportistas' },
              { id: 'sessions', label: '📋 Sesiones' },
              { id: 'designer', label: '✏️ Diseñador' },
              { id: 'settings', label: '⚙️ Configuración' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-4 py-4 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <>
            {/* KPI Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <KPICard
                title="Deportistas Activos"
                value={stats.activeAthletes}
                icon="👥"
                color="border-indigo-500"
              />
              <KPICard
                title="Sesiones Esta Semana"
                value={stats.sessionsThisWeek}
                icon="📋"
                color="border-green-500"
              />
              <KPICard
                title="Tasa de Completitud"
                value={stats.avgCompletionRate}
                icon="⭐"
                color="border-purple-500"
                suffix="%"
              />
            </div>

            {/* Recent Sessions Table */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-xl font-bold text-gray-900">Sesiones Recientes</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Deportista</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Tipo</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Duración</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Estado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    <tr className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-gray-900">Juan García</td>
                      <td className="px-6 py-4 text-gray-600">Fuerza</td>
                      <td className="px-6 py-4 text-gray-600">45 min</td>
                      <td className="px-6 py-4">
                        <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-semibold">
                          ✅ Completada
                        </span>
                      </td>
                    </tr>
                    <tr className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-gray-900">María López</td>
                      <td className="px-6 py-4 text-gray-600">Resistencia</td>
                      <td className="px-6 py-4 text-gray-600">30 min</td>
                      <td className="px-6 py-4">
                        <span className="px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-sm font-semibold">
                          ⏳ En Progreso
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* Athletes Tab */}
        {activeTab === 'athletes' && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <p className="text-4xl mb-4">📭</p>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Mis Deportistas</h2>
            <p className="text-gray-600 mb-6">No hay deportistas asignados aún</p>
            <button className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium">
              + Agregar Deportista
            </button>
          </div>
        )}

        {/* Sessions Tab */}
        {activeTab === 'sessions' && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <p className="text-4xl mb-4">📭</p>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Sesiones Recientes</h2>
            <p className="text-gray-600 mb-6">No hay sesiones registradas</p>
            <button className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium">
              + Nueva Sesión
            </button>
          </div>
        )}

        {/* Session Designer Tab */}
        {activeTab === 'designer' && <SessionDesigner />}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 max-w-2xl">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Configuración</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nombre</label>
                <input
                  type="text"
                  defaultValue={user?.name}
                  disabled
                  className="w-full px-4 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-600"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Correo</label>
                <input
                  type="email"
                  defaultValue={user?.email}
                  disabled
                  className="w-full px-4 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-600"
                />
              </div>
              <p className="text-sm text-gray-500 mt-4">
                Contacta al administrador para cambiar estos datos
              </p>
              <button
                onClick={logout}
                className="w-full mt-6 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
              >
                Cerrar sesión
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
