import { useState } from 'react'
import { useAuthStore } from '../store/authStore'

type Role = 'coach' | 'athlete'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [selectedRole, setSelectedRole] = useState<Role>('athlete')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const login = useAuthStore((state) => state.login)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    try {
      await login(email, password, selectedRole)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al iniciar sesión')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 via-purple-600 to-green-600 flex items-center justify-center p-4">
      {/* Main Card */}
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600 mb-2">
            FI-Stride
          </h1>
          <p className="text-gray-600">Entrenamiento personalizado para personas con T21</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Role Selector */}
          <div>
            <label className="block text-sm font-semibold text-gray-900 mb-3">
              ¿Cuál es tu rol?
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setSelectedRole('athlete')}
                className={`py-3 px-4 rounded-lg font-semibold transition-all duration-200 flex flex-col items-center gap-2 ${
                  selectedRole === 'athlete'
                    ? 'bg-blue-600 text-white ring-2 ring-blue-400'
                    : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                }`}
              >
                <span className="text-2xl">🏃</span>
                <span>Deportista</span>
              </button>
              <button
                type="button"
                onClick={() => setSelectedRole('coach')}
                className={`py-3 px-4 rounded-lg font-semibold transition-all duration-200 flex flex-col items-center gap-2 ${
                  selectedRole === 'coach'
                    ? 'bg-purple-600 text-white ring-2 ring-purple-400'
                    : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                }`}
              >
                <span className="text-2xl">👨‍🏫</span>
                <span>Entrenador</span>
              </button>
            </div>
          </div>

          {/* Email Input */}
          <div>
            <label htmlFor="email" className="block text-sm font-semibold text-gray-900 mb-2">
              Correo electrónico
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="tu@correo.com"
              required
              disabled={isLoading}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none transition disabled:bg-gray-100 disabled:cursor-not-allowed"
            />
          </div>

          {/* Password Input */}
          <div>
            <label htmlFor="password" className="block text-sm font-semibold text-gray-900 mb-2">
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              disabled={isLoading}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent outline-none transition disabled:bg-gray-100 disabled:cursor-not-allowed"
            />
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? '⏳ Iniciando sesión...' : '🚀 Entrar'}
          </button>
        </form>

        {/* Demo Credentials */}
        <div className="mt-8 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <p className="text-sm font-semibold text-gray-700 mb-2">📝 Demo Credentials:</p>
          <div className="text-xs text-gray-600 space-y-1">
            {selectedRole === 'athlete' ? (
              <>
                <p>
                  Deportista: <code className="bg-white px-2 py-1 rounded border border-gray-300">athlete@test.com</code> / <code className="bg-white px-2 py-1 rounded border border-gray-300">demo123</code>
                </p>
              </>
            ) : (
              <>
                <p>
                  Entrenador: <code className="bg-white px-2 py-1 rounded border border-gray-300">coach@test.com</code> / <code className="bg-white px-2 py-1 rounded border border-gray-300">demo123</code>
                </p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
