import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import styles from '../styles/login.module.css'

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
    <div className={styles.container}>
      <div className={styles.card}>
        <div className={styles.header}>
          <h1>FI-Stride</h1>
          <p>Entrenamiento personalizado para personas con T21</p>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          {/* Role Selector */}
          <div className={styles.roleSelector}>
            <p className={styles.label}>¿Cuál es tu rol?</p>
            <div className={styles.roleButtons}>
              <button
                type="button"
                className={`${styles.roleBtn} ${
                  selectedRole === 'athlete' ? styles.active : ''
                }`}
                onClick={() => setSelectedRole('athlete')}
              >
                <span className={styles.roleIcon}>🏃</span>
                <span>Deportista</span>
              </button>
              <button
                type="button"
                className={`${styles.roleBtn} ${
                  selectedRole === 'coach' ? styles.active : ''
                }`}
                onClick={() => setSelectedRole('coach')}
              >
                <span className={styles.roleIcon}>👨‍🏫</span>
                <span>Entrenador</span>
              </button>
            </div>
          </div>

          {/* Email Input */}
          <div className={styles.formGroup}>
            <label htmlFor="email" className={styles.label}>
              Correo electrónico
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="tu@correo.com"
              required
              className={styles.input}
              disabled={isLoading}
            />
          </div>

          {/* Password Input */}
          <div className={styles.formGroup}>
            <label htmlFor="password" className={styles.label}>
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              className={styles.input}
              disabled={isLoading}
            />
          </div>

          {/* Error Message */}
          {error && <div className={styles.error}>{error}</div>}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className={styles.submitBtn}
          >
            {isLoading ? 'Iniciando sesión...' : 'Entrar'}
          </button>
        </form>

        {/* Demo Credentials */}
        <div className={styles.demo}>
          <p className={styles.demoLabel}>Demo:</p>
          <p>
            {selectedRole === 'athlete' ? (
              <>
                Deportista: <code>athlete@test.com</code> / <code>demo123</code>
              </>
            ) : (
              <>
                Entrenador: <code>coach@test.com</code> / <code>demo123</code>
              </>
            )}
          </p>
        </div>
      </div>

      {/* Background Gradient */}
      <div className={styles.gradientBg}></div>
    </div>
  )
}
