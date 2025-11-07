/**
 * Theme Hook - Manages coach/athlete mode switching
 * Sets data-mode attribute on root for CSS variable switching
 */

import { useEffect } from 'react'
import { useAuthStore } from '../store/authStore'

export type Theme = 'coach' | 'athlete'

export interface UseThemeReturn {
  theme: Theme
  toggleTheme: (theme: Theme) => void
  isDarkMode: boolean
  toggleDarkMode: () => void
}

export function useTheme(): UseThemeReturn {
  const user = useAuthStore((state) => state.user)

  // Determine theme based on user role
  const theme = (user?.role === 'coach' ? 'coach' : 'athlete') as Theme

  // Initialize theme on mount
  useEffect(() => {
    document.documentElement.setAttribute('data-mode', theme)
  }, [theme])

  // Toggle theme function (for future preference overrides)
  const toggleTheme = (newTheme: Theme) => {
    document.documentElement.setAttribute('data-mode', newTheme)
  }

  // Dark mode toggle (for future dark mode support)
  const isDarkMode = localStorage.getItem('fi-stride-dark-mode') === 'true'

  const toggleDarkMode = () => {
    const newState = !isDarkMode
    localStorage.setItem('fi-stride-dark-mode', String(newState))
    if (newState) {
      document.documentElement.setAttribute('data-dark', 'true')
    } else {
      document.documentElement.removeAttribute('data-dark')
    }
  }

  return {
    theme,
    toggleTheme,
    isDarkMode,
    toggleDarkMode,
  }
}
