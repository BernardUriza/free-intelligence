import { useState, useEffect, useCallback } from 'react'
import { invoke, listen, isTauriContext } from '../lib/tauri-adapter'
import { SERVICE_URLS } from '../lib/constants'
import type { ServiceStatus, RagStats } from '../types/monitor'

export function useServiceStatus() {
  const [status, setStatus] = useState<ServiceStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [ragStats, setRagStats] = useState<RagStats | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      setError(null)
      const result = await invoke<ServiceStatus>('get_status')
      setStatus(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  // Main status polling
  useEffect(() => {
    if (!isTauriContext()) {
      console.warn('[App] Browser mode: detecting services via HTTP')
      setLoading(false)

      const detectServices = async () => {
        let ollamaRunning = false
        let ollamaModels: string[] = []
        let ragRunning = false

        try {
          const ollamaRes = await fetch(`${SERVICE_URLS.OLLAMA}/api/tags`, {
            signal: AbortSignal.timeout(2000)
          })
          if (ollamaRes.ok) {
            const data = await ollamaRes.json()
            ollamaRunning = true
            ollamaModels = data.models?.map((m: { name: string }) => m.name) || []
            console.log('[App] Ollama detected:', ollamaModels.length, 'models')
          }
        } catch (err) {
          console.warn('[App] Ollama not detected:', err)
        }

        try {
          const ragRes = await fetch(`${SERVICE_URLS.RAG}/rag/health`, {
            signal: AbortSignal.timeout(2000)
          })
          ragRunning = ragRes.ok
          console.log('[App] RAG Service detected:', ragRunning)
        } catch (err) {
          console.warn('[App] RAG Service not detected:', err)
        }

        setStatus({
          ollama_running: ollamaRunning,
          ollama_models: ollamaModels,
          tunnel_running: false,
          tunnel_url: null,
          rag_service_running: ragRunning,
          gateway_running: false,
          system_info: { platform: 'browser', hostname: 'localhost' }
        })
      }

      detectServices()
      const interval = setInterval(detectServices, 5000)
      return () => clearInterval(interval)
    }

    fetchStatus()
    const interval = setInterval(fetchStatus, 5000)
    const unlistenServices = listen('services-checked', () => fetchStatus())
    const unlistenTunnel = listen('tunnel-started', () => fetchStatus())
    const unlistenTunnelUrl = listen<string>('tunnel-url-found', (event) => {
      setStatus(prev => prev ? { ...prev, tunnel_url: event.payload } : prev)
    })
    return () => {
      clearInterval(interval)
      unlistenServices.then(fn => fn())
      unlistenTunnel.then(fn => fn())
      unlistenTunnelUrl.then(fn => fn())
    }
  }, [fetchStatus])

  // RAG stats polling
  useEffect(() => {
    if (!isTauriContext()) {
      console.warn('[App] Skipping RAG stats polling (not in Tauri context)')
      return
    }

    if (!status?.rag_service_running) {
      setRagStats(null)
      return
    }

    const fetchRagStats = async () => {
      try {
        const stats = await invoke<RagStats>('get_rag_stats')
        setRagStats(stats)
      } catch (err) {
        console.error('[FI Monitor] Failed to fetch RAG stats:', err)
        setRagStats(null)
      }
    }

    fetchRagStats()
    const interval = setInterval(fetchRagStats, 5000)
    return () => clearInterval(interval)
  }, [status?.rag_service_running])

  const handleAction = async (action: string, command: string) => {
    if (!isTauriContext()) {
      setError('Action not available in browser mode')
      return
    }

    setActionLoading(action)
    try {
      await invoke(command)
      await fetchStatus()
    } catch (err) {
      setError(String(err))
    } finally {
      setActionLoading(null)
    }
  }

  return {
    status,
    loading,
    error,
    setError,
    actionLoading,
    setActionLoading,
    ragStats,
    handleAction,
    fetchStatus,
  }
}
