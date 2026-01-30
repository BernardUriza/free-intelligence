// Tauri API adapter - direct imports from @tauri-apps/api
import { invoke as tauriInvoke } from '@tauri-apps/api/core'
import { listen as tauriListen } from '@tauri-apps/api/event'
import { getVersion as tauriGetVersion } from '@tauri-apps/api/app'

// Check if we're running in Tauri context
const isTauri = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window

// Safe wrappers that check Tauri availability
export const invoke: typeof tauriInvoke = async (...args: any[]) => {
  if (!isTauri) {
    throw new Error('Tauri APIs are only available in the Tauri app context')
  }
  return tauriInvoke(...args)
}

export const listen: typeof tauriListen = async (...args: any[]) => {
  if (!isTauri) {
    throw new Error('Tauri APIs are only available in the Tauri app context')
  }
  return tauriListen(...args)
}

export const getVersion: typeof tauriGetVersion = async () => {
  if (!isTauri) {
    throw new Error('Tauri APIs are only available in the Tauri app context')
  }
  return tauriGetVersion()
}

// Export helper to check if Tauri is available
export const isTauriContext = () => isTauri
