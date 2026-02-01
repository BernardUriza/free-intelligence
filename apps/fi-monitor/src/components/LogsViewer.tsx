// Real-time logs viewer for services
import { useState, useEffect, useRef } from 'react'
import { invoke, listen } from '../lib/tauri-adapter'

interface LogEntry {
  timestamp: string
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG'
  service: string
  message: string
}

interface LogsViewerProps {
  serviceName: string
  serviceDisplayName: string
}

export function LogsViewer({ serviceName, serviceDisplayName }: LogsViewerProps) {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [autoScroll, setAutoScroll] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [isExpanded, setIsExpanded] = useState(false)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Load initial logs when expanded
  useEffect(() => {
    if (isExpanded) {
      loadLogs()
    }
  }, [isExpanded, serviceName])

  // Listen for real-time log events
  useEffect(() => {
    if (!isExpanded) return

    const unlisten = listen<LogEntry>(`log-${serviceName}`, (event) => {
      setLogs(prev => {
        const newLogs = [...prev, event.payload]
        // Keep only last 200 lines (memory optimization)
        return newLogs.slice(-200)
      })
    })

    return () => {
      unlisten.then(fn => fn())
    }
  }, [isExpanded, serviceName])

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  const loadLogs = async () => {
    try {
      const initialLogs = await invoke<LogEntry[]>('get_service_logs', {
        service: serviceName,
        lines: 50
      })
      setLogs(initialLogs)
    } catch (err) {
      console.error('[LogsViewer] Failed to load logs:', err)
    }
  }

  const clearLogs = () => {
    setLogs([])
  }

  const exportLogs = () => {
    const content = logs.map(log =>
      `[${log.timestamp}] [${log.level}] ${log.message}`
    ).join('\n')

    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${serviceName}-logs-${Date.now()}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  const filteredLogs = searchQuery
    ? logs.filter(log =>
        log.message.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : logs

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR': return 'log-error'
      case 'WARN': return 'log-warn'
      case 'INFO': return 'log-info'
      case 'DEBUG': return 'log-debug'
      default: return ''
    }
  }

  return (
    <div className="logs-viewer">
      <button
        className="logs-toggle"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? '▼' : '▶'} Show Logs
      </button>

      {isExpanded && (
        <div className="logs-panel">
          {/* Controls */}
          <div className="logs-controls">
            <input
              type="text"
              placeholder="Search logs... (Ctrl+F)"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="logs-search"
            />

            <div className="logs-actions">
              <button
                onClick={() => setAutoScroll(!autoScroll)}
                className={autoScroll ? 'active' : ''}
                title="Auto-scroll to bottom"
              >
                {autoScroll ? '⏸️ Pause' : '▶️ Resume'}
              </button>

              <button onClick={clearLogs} title="Clear logs">
                🗑️ Clear
              </button>

              <button onClick={exportLogs} title="Export logs">
                💾 Export
              </button>

              <span className="logs-count">
                {filteredLogs.length} lines
              </span>
            </div>
          </div>

          {/* Log entries */}
          <div className="logs-container" ref={containerRef}>
            {filteredLogs.length === 0 ? (
              <div className="logs-empty">
                {searchQuery
                  ? `No logs matching "${searchQuery}"`
                  : 'No logs available. Service may not be running.'}
              </div>
            ) : (
              filteredLogs.map((log, idx) => (
                <div key={idx} className={`log-entry ${getLevelColor(log.level)}`}>
                  <span className="log-timestamp">{log.timestamp}</span>
                  <span className="log-level">[{log.level}]</span>
                  <span className="log-message">{log.message}</span>
                </div>
              ))
            )}
            <div ref={logsEndRef} />
          </div>
        </div>
      )}
    </div>
  )
}
