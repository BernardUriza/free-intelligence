import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

/**
 * Navigation Bar Component
 * Displays role-based navigation links
 *
 * Features:
 * - Role-based menu (Coach vs Athlete)
 * - Logo/home link
 * - Accessibility-friendly
 * - Mobile responsive
 */

export function Navbar() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)

  if (!user) {
    return null
  }

  const isCoach = user.role === 'coach'

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <nav className="bg-slate-900 border-b border-slate-700 sticky top-0 z-50 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo / Home */}
          <button
            onClick={() => navigate(isCoach ? '/coach' : '/')}
            className="flex items-center gap-2 hover:opacity-80 transition-opacity"
            aria-label="FI-Stride Home"
          >
            <span className="text-2xl">🎯</span>
            <span className="text-white font-bold text-lg hidden sm:inline">FI-Stride</span>
          </button>

          {/* Main Nav Links */}
          <div className="flex items-center gap-4">
            {/* Biblioteca */}
            <button
              onClick={() => navigate('/biblioteca')}
              className="px-3 py-2 text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800 rounded-md transition-colors"
              aria-label="Biblioteca de Ejercicios"
            >
              📚 Biblioteca
            </button>

            {/* Coach Dashboard (only for coaches) */}
            {isCoach && (
              <button
                onClick={() => navigate('/coach')}
                className="px-3 py-2 text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800 rounded-md transition-colors"
                aria-label="Panel del Entrenador"
              >
                👨‍🏫 Panel
              </button>
            )}

            {/* T21 Resources */}
            <button
              onClick={() => navigate('/t21/inicio')}
              className="px-3 py-2 text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800 rounded-md transition-colors"
              aria-label="Recursos T21"
            >
              ♿ T21
            </button>

            {/* Privacy */}
            <button
              onClick={() => navigate('/privacidad')}
              className="px-3 py-2 text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800 rounded-md transition-colors"
              aria-label="Privacidad"
            >
              🔒 Privacidad
            </button>

            {/* User Menu (Logout) */}
            <div className="border-l border-slate-700 pl-4">
              <button
                onClick={handleLogout}
                className="px-3 py-2 text-sm font-medium text-red-400 hover:text-red-300 hover:bg-slate-800 rounded-md transition-colors"
                aria-label="Cerrar sesión"
                title={`Logged in as ${user.name}`}
              >
                👋 Salir
              </button>
            </div>
          </div>
        </div>
      </div>
    </nav>
  )
}
