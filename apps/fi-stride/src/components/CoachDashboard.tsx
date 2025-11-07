import { useState } from 'react'
import { useAuthStore } from '../store/authStore'

interface CoachStats {
  activeAthletes: number
  sessionsThisWeek: number
  avgCompletionRate: number
}

export function CoachDashboard() {
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const [activeTab, setActiveTab] = useState<'overview' | 'athletes' | 'sessions' | 'settings'>('overview')

  // Mock stats - en producción vendrían del backend
  const stats: CoachStats = {
    activeAthletes: 12,
    sessionsThisWeek: 8,
    avgCompletionRate: 87,
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-16 z-40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-slate-900">👨‍🏫 Panel de Entrenador</h1>
              <p className="text-slate-600 mt-1">Gestiona tus deportistas y sesiones</p>
            </div>
            <div className="text-right">
              <p className="text-sm text-slate-600">Hola, {user?.name}</p>
            </div>
          </div>
        </div>
      </header>

      {/* Tabs Navigation */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex gap-8">
            <button
              onClick={() => setActiveTab('overview')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'overview'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-slate-600 hover:text-slate-900'
              }`}
            >
              📊 Overview
            </button>
            <button
              onClick={() => setActiveTab('athletes')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'athletes'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-slate-600 hover:text-slate-900'
              }`}
            >
              👥 Deportistas
            </button>
            <button
              onClick={() => setActiveTab('sessions')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'sessions'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-slate-600 hover:text-slate-900'
              }`}
            >
              📋 Sesiones
            </button>
            <button
              onClick={() => setActiveTab('settings')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'settings'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-slate-600 hover:text-slate-900'
              }`}
            >
              ⚙️ Configuración
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-8">
            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Card 1: Active Athletes */}
              <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-slate-600 text-sm font-medium">Deportistas Activos</p>
                    <p className="text-3xl font-bold text-slate-900 mt-2">{stats.activeAthletes}</p>
                  </div>
                  <span className="text-4xl">👥</span>
                </div>
                <p className="text-slate-500 text-xs mt-4">Monitoreando progreso en tiempo real</p>
              </div>

              {/* Card 2: Sessions This Week */}
              <div className="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-slate-600 text-sm font-medium">Sesiones Esta Semana</p>
                    <p className="text-3xl font-bold text-slate-900 mt-2">{stats.sessionsThisWeek}</p>
                  </div>
                  <span className="text-4xl">📋</span>
                </div>
                <p className="text-slate-500 text-xs mt-4">Completadas y en progreso</p>
              </div>

              {/* Card 3: Completion Rate */}
              <div className="bg-white rounded-lg shadow p-6 border-l-4 border-purple-500">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-slate-600 text-sm font-medium">Tasa de Completitud</p>
                    <p className="text-3xl font-bold text-slate-900 mt-2">{stats.avgCompletionRate}%</p>
                  </div>
                  <span className="text-4xl">⭐</span>
                </div>
                <div className="mt-4 bg-slate-200 rounded-full h-2 w-full">
                  <div
                    className="bg-purple-500 h-2 rounded-full"
                    style={{ width: `${stats.avgCompletionRate}%` }}
                  ></div>
                </div>
              </div>
            </div>

            {/* Recent Sessions */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-6 border-b border-slate-200">
                <h2 className="text-xl font-bold text-slate-900">Sesiones Recientes</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase">Deportista</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase">Tipo</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase">Duración</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase">Estado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    <tr className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 text-slate-900">Juan García</td>
                      <td className="px-6 py-4 text-slate-600">Fuerza</td>
                      <td className="px-6 py-4 text-slate-600">45 min</td>
                      <td className="px-6 py-4"><span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-xs font-semibold">✅ Completada</span></td>
                    </tr>
                    <tr className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 text-slate-900">María López</td>
                      <td className="px-6 py-4 text-slate-600">Resistencia</td>
                      <td className="px-6 py-4 text-slate-600">30 min</td>
                      <td className="px-6 py-4"><span className="bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-xs font-semibold">⏳ En Progreso</span></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Athletes Tab */}
        {activeTab === 'athletes' && (
          <section className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-slate-900 mb-6">Mis Deportistas</h2>
            <div className="text-center py-12">
              <p className="text-slate-600 mb-4">📭 No hay deportistas asignados aún</p>
              <button className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-lg transition-colors">
                + Agregar Deportista
              </button>
            </div>
          </section>
        )}

        {/* Sessions Tab */}
        {activeTab === 'sessions' && (
          <section className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-slate-900 mb-6">Sesiones Recientes</h2>
            <div className="text-center py-12">
              <p className="text-slate-600 mb-4">📭 No hay sesiones registradas</p>
              <button className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-6 rounded-lg transition-colors">
                + Nueva Sesión
              </button>
            </div>
          </section>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <section className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-slate-900 mb-6">Configuración</h2>
            <div className="max-w-md space-y-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Nombre</label>
                <input
                  type="text"
                  defaultValue={user?.name}
                  disabled
                  className="w-full px-4 py-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-600"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Correo</label>
                <input
                  type="email"
                  defaultValue={user?.email}
                  disabled
                  className="w-full px-4 py-2 bg-slate-100 border border-slate-300 rounded-lg text-slate-600"
                />
              </div>
              <p className="text-sm text-slate-500">
                Contacta al administrador para cambiar estos datos
              </p>
              <button
                onClick={logout}
                className="w-full bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-6 rounded-lg transition-colors"
              >
                Cerrar sesión
              </button>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}
