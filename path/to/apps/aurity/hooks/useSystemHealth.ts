import { useState, useEffect } from 'react';

interface SystemHealth {
  ollama: 'online' | 'offline';
  backend: 'online' | 'offline';
  isHealthy: boolean;
}

const useSystemHealth = (): SystemHealth => {
  const [health, setHealth] = useState<SystemHealth>({
    ollama: 'unknown',
    backend: 'unknown',
    isHealthy: false,
  });

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const ollamaResponse = await fetch('http://localhost:11434/api/tags');
        const backendResponse = await fetch('http://localhost:7001/api/health');

        setHealth({
          ...health,
          ollama: ollamaResponse.ok ? 'online' : 'offline',
          backend: backendResponse.ok ? 'online' : 'offline',
          isHealthy: ollamaResponse.ok && backendResponse.ok,
        });
      } catch (error) {
        console.error('Error checking system health:', error);
        setHealth({
          ...health,
          ollama: 'unknown',
          backend: 'unknown',
          isHealthy: false,
        });
      }
    };

    const intervalId = setInterval(checkStatus, 30000);

    return () => clearInterval(intervalId);
  }, []);

  return health;
};

export default useSystemHealth;
