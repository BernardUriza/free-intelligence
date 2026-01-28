// Tauri API adapter - works in both Tauri and web mode
import { mockInvoke, mockListen, mockGetVersion } from '../mocks/tauri'

// Type definitions
type InvokeFn = <T = any>(cmd: string, args?: Record<string, any>) => Promise<T>
type ListenFn = <T = any>(event: string, handler: (event: { payload: T }) => void) => Promise<() => void>
type GetVersionFn = () => Promise<string>

export const isTauri = typeof window !== 'undefined' && '__TAURI__' in window

// Try to import real Tauri API, fallback to mocks
let realInvoke: InvokeFn | undefined
let realListen: ListenFn | undefined
let realGetVersion: GetVersionFn | undefined

try {
  if (isTauri) {
    const core = require('@tauri-apps/api/core')
    const event = require('@tauri-apps/api/event')
    const app = require('@tauri-apps/api/app')
    realInvoke = core.invoke as InvokeFn
    realListen = event.listen as ListenFn
    realGetVersion = app.getVersion as GetVersionFn
  }
} catch (error) {
  console.log('[Tauri Adapter] Running in web mode, using mocks')
}

export const invoke: InvokeFn = realInvoke || mockInvoke
export const listen: ListenFn = realListen || mockListen
export const getVersion: GetVersionFn = realGetVersion || mockGetVersion
