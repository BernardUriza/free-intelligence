'use client';

import { useEffect, useState } from 'react';
import { Waves, TreePine, Mountain, Sunset, Flower2, Star } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface Scene {
  icon: LucideIcon;
  label: string;
  subtitle: string;
  color: string;
}

const scenes: Scene[] = [
  { icon: Waves, label: 'Olas del océano', subtitle: 'Déjate llevar por la calma del mar', color: 'from-blue-600/30 to-cyan-600/20' },
  { icon: TreePine, label: 'Bosque tranquilo', subtitle: 'Conecta con la naturaleza', color: 'from-green-600/30 to-emerald-600/20' },
  { icon: Mountain, label: 'Montañas serenas', subtitle: 'Encuentra tu paz interior', color: 'from-slate-600/30 to-blue-600/20' },
  { icon: Sunset, label: 'Atardecer dorado', subtitle: 'Un momento de serenidad', color: 'from-orange-600/30 to-pink-600/20' },
  { icon: Flower2, label: 'Jardín zen', subtitle: 'Armonía y equilibrio', color: 'from-pink-600/30 to-rose-600/20' },
  { icon: Star, label: 'Cielo estrellado', subtitle: 'Infinitas posibilidades', color: 'from-indigo-600/30 to-purple-600/20' },
];

export function CalmingNatureWidget() {
  const [currentScene, setCurrentScene] = useState(0);

  useEffect(() => {
    let isActive = true;
    const timer = setInterval(() => {
      if (!isActive) return;
      setCurrentScene(prev => (prev + 1) % scenes.length);
    }, 8000);
    return () => {
      isActive = false;
      clearInterval(timer);
    };
  }, []);

  const scene = scenes[currentScene];

  return (
    <div className={`wgt-calming-card bg-gradient-to-br ${scene.color}`}>
      <div className="wgt-calming-icon">
        <scene.icon style={{ width: 'clamp(6rem, 20vw, 16rem)', height: 'clamp(6rem, 20vw, 16rem)' }} strokeWidth={1} />
      </div>

      <h3 className="wgt-calming-title" style={{ fontSize: 'clamp(1.5rem, 4vw, 4rem)' }}>
        {scene.label}
      </h3>

      <p className="fi-text mb-4 sm:mb-6" style={{ fontSize: 'clamp(0.875rem, 2vw, 2rem)' }}>
        {scene.subtitle}
      </p>

      <div className="wgt-calming-hint">
        <div className="wgt-calming-ping" />
        <span style={{ fontSize: 'clamp(0.75rem, 1.5vw, 1.25rem)' }}>
          Respira profundo y relájate
        </span>
      </div>

      <div className="wgt-calming-dots">
        {scenes.map((_, index) => (
          <div
            key={index}
            className={`w-2 h-2 sm:w-3 sm:h-3 rounded-full transition-all duration-500 ${
              index === currentScene ? 'bg-white scale-125' : 'bg-white/30'
            }`}
          />
        ))}
      </div>
    </div>
  );
}
