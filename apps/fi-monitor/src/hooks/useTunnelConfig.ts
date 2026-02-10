import { useState, useEffect } from 'react'
import { invoke, isTauriContext } from '../lib/tauri-adapter'

export function useTunnelConfig(tunnelRunning?: boolean, tunnelUrl?: string | null) {
  const [tunnelPort, setTunnelPort] = useState('11400')
  const [tunnelPortError, setTunnelPortError] = useState<string | null>(null)
  const [savedTunnelPort, setSavedTunnelPort] = useState('11400')
  const [tunnelFileContent, setTunnelFileContent] = useState<string>('')

  // Load tunnel port on mount
  useEffect(() => {
    if (!isTauriContext()) {
      console.warn('[App] Skipping tunnel port load (not in Tauri context)')
      return
    }
    invoke<number>('get_tunnel_port')
      .then(port => {
        setTunnelPort(String(port))
        setSavedTunnelPort(String(port))
      })
      .catch(err => console.error('[FI Monitor] Failed to load tunnel port:', err))
  }, [])

  const loadTunnelFile = async () => {
    if (!isTauriContext()) {
      setTunnelFileContent('Not available in browser mode')
      return
    }

    try {
      const content = await invoke<string>('read_tunnel_file')
      const parsed = JSON.parse(content)
      setTunnelFileContent(JSON.stringify(parsed, null, 2))
    } catch (error) {
      console.error('Failed to read tunnel file:', error)
      setTunnelFileContent(`Error: ${String(error)}`)
    }
  }

  // Auto-load tunnel file (always try, even when tunnel is OFF)
  useEffect(() => {
    loadTunnelFile()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tunnelRunning, tunnelUrl])

  const handleSaveTunnelPort = async () => {
    if (!isTauriContext()) {
      setTunnelPortError('Not available in browser mode')
      return
    }

    setTunnelPortError(null)

    const port = parseInt(tunnelPort, 10)
    if (isNaN(port)) {
      setTunnelPortError('Port must be a number')
      return
    }
    if (port < 1024 || port > 65535) {
      setTunnelPortError('Port must be between 1024-65535')
      return
    }

    try {
      await invoke('set_tunnel_port', { port })
      setSavedTunnelPort(tunnelPort)
      setTunnelPortError(null)
    } catch (err) {
      setTunnelPortError(String(err))
    }
  }

  return {
    tunnelPort,
    setTunnelPort,
    tunnelPortError,
    setTunnelPortError,
    savedTunnelPort,
    tunnelFileContent,
    handleSaveTunnelPort,
    loadTunnelFile,
  }
}
