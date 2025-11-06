import { useEffect } from 'react'
import { useAuthStore } from './store/authStore'
import { LoginPage } from './components/LoginPage'
import { CoachDashboard } from './components/CoachDashboard'
import { AthleteFlow } from './components/AthleteFlow'
import './App.css'

/**
 * FI-Stride Main App Component (Multiplexor)
 *
 * Routing logic:
 * 1. If not authenticated -> LoginPage (role selector + auth)
 * 2. If authenticated && role === 'coach' -> CoachDashboard
 * 3. If authenticated && role === 'athlete' -> AthleteFlow
 */
function App() {
  const user = useAuthStore((state) => state.user)
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const setUser = useAuthStore((state) => state.setUser)

  // Load user from localStorage on mount
  useEffect(() => {
    const savedUser = localStorage.getItem('fi-stride-user')
    if (savedUser) {
      try {
        const user = JSON.parse(savedUser)
        setUser(user)
      } catch (err) {
        console.error('Failed to restore user session:', err)
      }
    }
  }, [setUser])

  // Route based on authentication and role
  if (!isAuthenticated || !user) {
    return <LoginPage />
  }

  if (user.role === 'coach') {
    return <CoachDashboard />
  }

  if (user.role === 'athlete') {
    return <AthleteFlow />
  }

  // Fallback (should not reach here)
  return <LoginPage />
}

export default App
