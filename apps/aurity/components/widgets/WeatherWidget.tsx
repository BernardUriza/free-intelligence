'use client';

import { useEffect, useState } from 'react';

interface WeatherWidgetProps {
  city?: string;
}

export function WeatherWidget({ city = 'Ciudad de México' }: WeatherWidgetProps) {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Mock weather data (in real app, would fetch from API)
  const weather = {
    temp: 22,
    condition: 'Soleado',
    icon: '☀️',
    humidity: 45,
  };

  const formattedTime = currentTime.toLocaleTimeString('es-MX', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  const formattedDate = currentTime.toLocaleDateString('es-MX', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  return (
    <div className="bg-gradient-to-br from-blue-950/40 to-cyan-950/40 border border-blue-600/40 rounded-xl p-6 backdrop-blur-sm">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-5xl font-bold text-white mb-2 font-mono">
            {formattedTime}
          </div>
          <div className="text-sm text-blue-300 capitalize">
            {formattedDate}
          </div>
        </div>

        <div className="text-right">
          <div className="text-6xl mb-2">{weather.icon}</div>
          <div className="text-3xl font-bold text-white">{weather.temp}°C</div>
          <div className="text-sm text-blue-300">{weather.condition}</div>
          <div className="text-xs fi-text-primary/60 mt-1">
            Humedad: {weather.humidity}%
          </div>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-blue-700/30">
        <div className="fi-flex-gap text-blue-300 text-sm">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
          </svg>
          <span>{city}</span>
        </div>
      </div>
    </div>
  );
}
