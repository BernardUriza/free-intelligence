// User roles
export type UserRole = 'coach' | 'athlete'

// User authentication
export interface User {
  id: string
  name: string
  email: string
  role: UserRole
  avatar?: string
  createdAt: Date
}

// Session for athletes
export interface Session {
  id: string
  athleteId: string
  coachId: string
  name: string
  duration: number // minutes
  rpe?: number // Rate of Perceived Exertion (1-10)
  emotionalCheckIn?: string
  achievements?: string[]
  startedAt: Date
  completedAt?: Date
  status: 'draft' | 'active' | 'completed'
}

// Consent data (from athlete flow)
export interface ConsentData {
  userId: string
  privacyAccepted: boolean
  encryptionUnderstood: boolean
  cameraAllowed: boolean
  micAllowed: boolean
  timestamp: Date
}

// App authentication state
export interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
}

// Coach data
export interface Coach {
  id: string
  name: string
  email: string
  athletes: string[] // athlete IDs
  createdAt: Date
}

// Athlete data
export interface Athlete {
  id: string
  name: string
  coachId: string
  age: number
  lastSessionDate?: Date
  sessionsCompleted: number
  createdAt: Date
}
