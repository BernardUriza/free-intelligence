'use client';

import { useEffect, useState } from 'react';
import { Sun, MapPin } from 'lucide-react';

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
          <div className="mb-2 text-yellow-400">
            <Sun className="w-14 h-14 ml-auto" strokeWidth={1.5} />
          </div>
          <div className="text-3xl font-bold text-white">{weather.temp}°C</div>
          <div className="text-sm text-blue-300">{weather.condition}</div>
          <div className="text-xs fi-text-primary/60 mt-1">
            Humedad: {weather.humidity}%
          </div>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-blue-700/30">
        <div className="fi-flex-gap text-blue-300 text-sm">
          <MapPin className="w-4 h-4" strokeWidth={1.5} />
          <span>{city}</span>
        </div>
      </div>
    </div>
  );
}
