import { create } from 'zustand'
import { User, AuthState } from '../types'

interface AuthStore extends AuthState {
  login: (email: string, password: string, role: 'coach' | 'athlete') => Promise<void>
  logout: () => void
  setUser: (user: User | null) => void
  setError: (error: string | null) => void
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (email: string, _password: string, role: 'coach' | 'athlete') => {
    set({ isLoading: true, error: null })
    try {
      // TODO: Integrate with FI Backend API
      // const response = await fetch('/api/auth/login', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ email, password, role })
      // })

      // Mock login for development
      const mockUser: User = {
        id: `${role}-${Date.now()}`,
        name: email.split('@')[0],
        email,
        role,
        createdAt: new Date()
      }

      set({
        user: mockUser,
        isAuthenticated: true,
        isLoading: false
      })

      // Store in localStorage
      localStorage.setItem('fi-stride-user', JSON.stringify(mockUser))
      localStorage.setItem('fi-stride-auth-token', `token-${mockUser.id}`)
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Login failed',
        isLoading: false
      })
      throw error
    }
  },

  logout: () => {
    set({
      user: null,
      isAuthenticated: false,
      error: null
    })
    localStorage.removeItem('fi-stride-user')
    localStorage.removeItem('fi-stride-auth-token')
  },

  setUser: (user: User | null) => {
    set({
      user,
      isAuthenticated: !!user
    })
  },

  setError: (error: string | null) => {
    set({ error })
  }
}))
