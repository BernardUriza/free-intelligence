import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import { useTheme } from './hooks/useTheme'
import { LoginPage } from './components/LoginPage'
import { CoachDashboard } from './components/CoachDashboard'
import { AthleteFlow } from './components/AthleteFlow'
import { Library } from './pages/Library'
import { Privacy } from './pages/Privacy'
import { T21Resources } from './pages/T21Resources'
import { Navbar } from './components/Navbar'
import { OfflineStatusBar } from './components/OfflineStatusBar'
import './styles/design-tokens.css'
import './App.css'

/**
 * FI-Stride Main App Component (Router + Multiplexor)
 *
 * Routing structure:
 * - / -> Login (public)
 * - /athlete/* -> AthleteFlow & related (authenticated, athlete role)
 * - /coach/* -> CoachDashboard (authenticated, coach role)
 * - /biblioteca -> Library (authenticated)
 * - /privacidad -> Privacy (public)
 * - /t21/* -> T21 Resources (public)
 */

function AppContent() {
  const user = useAuthStore((state) => state.user)
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const [isLoading, setIsLoading] = useState(true)
  const setUser = useAuthStore((state) => state.setUser)

  // Initialize theme based on user role
  useTheme()

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
    setIsLoading(false)
  }, [setUser])

  if (isLoading) {
    return <div>Cargando...</div>
  }

  // Route based on authentication and role
  if (!isAuthenticated || !user) {
    return (
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route path="/privacidad" element={<Privacy />} />
        <Route path="/t21/*" element={<T21Resources />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    )
  }

  // Authenticated routes - with Navbar visible
  if (user.role === 'coach') {
    return (
      <>
        <Navbar />
        <Routes>
          <Route path="/coach" element={<CoachDashboard />} />
          <Route path="/biblioteca" element={<Library />} />
          <Route path="/privacidad" element={<Privacy />} />
          <Route path="/t21/*" element={<T21Resources />} />
          <Route path="*" element={<Navigate to="/coach" replace />} />
        </Routes>
      </>
    )
  }

  if (user.role === 'athlete') {
    return (
      <>
        <Navbar />
        <Routes>
          <Route path="/" element={<AthleteFlow />} />
          <Route path="/biblioteca" element={<Library />} />
          <Route path="/privacidad" element={<Privacy />} />
          <Route path="/t21/*" element={<T21Resources />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </>
    )
  }

  // Fallback
  return <Navigate to="/" replace />
}

function App() {
  return (
    <BrowserRouter>
      <AppContent />
      <OfflineStatusBar />
    </BrowserRouter>
  )
}

export default App
