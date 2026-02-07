// Tauri API adapter - direct imports from @tauri-apps/api
import { invoke as tauriInvoke, type InvokeArgs } from '@tauri-apps/api/core'
import { listen as tauriListen, type EventCallback, type UnlistenFn } from '@tauri-apps/api/event'
import { getVersion as tauriGetVersion } from '@tauri-apps/api/app'

// Check if we're running in Tauri context
const isTauri = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window

// Safe wrappers that check Tauri availability
export async function invoke<T>(cmd: string, args?: InvokeArgs): Promise<T> {
  if (!isTauri) {
    throw new Error('Tauri APIs are only available in the Tauri app context')
  }
  return tauriInvoke<T>(cmd, args)
}

export async function listen<T>(event: string, handler: EventCallback<T>): Promise<UnlistenFn> {
  if (!isTauri) {
    throw new Error('Tauri APIs are only available in the Tauri app context')
  }
  return tauriListen<T>(event, handler)
}

export async function getVersion(): Promise<string> {
  if (!isTauri) {
    throw new Error('Tauri APIs are only available in the Tauri app context')
  }
  return tauriGetVersion()
}

// Export helper to check if Tauri is available
export const isTauriContext = () => isTauri
