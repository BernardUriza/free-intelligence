// Tauri API adapter - direct imports from @tauri-apps/api
import { invoke as tauriInvoke } from '@tauri-apps/api/core'
import { listen as tauriListen } from '@tauri-apps/api/event'
import { getVersion as tauriGetVersion } from '@tauri-apps/api/app'

// Re-export Tauri APIs directly
export const invoke = tauriInvoke
export const listen = tauriListen
export const getVersion = tauriGetVersion
