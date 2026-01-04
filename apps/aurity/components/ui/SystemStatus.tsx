'use client';

import { useState, useEffect } from 'react';

export function SystemStatus() {
  const [status, setStatus] = useState<'checking' | 'online' | 'offline'>('checking');

  useEffect(() => {
    const checkOllamaStatus = async () => {
      try {
        const res = await fetch('http://localhost:11434/api/tags');
        setStatus(res.ok ? 'online' : 'offline');
      } catch {
        setStatus('offline');
      }
    };

    checkOllamaStatus();
    const intervalId = setInterval(checkOllamaStatus, 30000);
    return () => clearInterval(intervalId);
  }, []);

  const statusConfig = {
    checking: { color: 'bg-yellow-500', label: 'Ollama: Verificando...' },
    online: { color: 'bg-green-500', label: 'Ollama: Online' },
    offline: { color: 'bg-red-500', label: 'Ollama: Offline' },
  };

  const { color, label } = statusConfig[status];

  return (
    <div className="relative group" title={label}>
      <div className={`w-2.5 h-2.5 rounded-full ${color} ${status === 'checking' ? 'animate-pulse' : ''}`} />
      {/* Tooltip */}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-slate-800 text-xs text-slate-200 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
        {label}
      </div>
    </div>
  );
}

export default SystemStatus;
