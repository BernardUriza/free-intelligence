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
    <div className={`h-full flex flex-col items-center justify-center bg-gradient-to-br ${scene.color} border border-slate-700/50 rounded-xl backdrop-blur-sm text-center transition-all duration-1000 p-4 sm:p-6 lg:p-8`}>
      <div className="animate-pulse mb-4 sm:mb-6 lg:mb-8 text-white/80">
        <scene.icon style={{ width: 'clamp(6rem, 20vw, 16rem)', height: 'clamp(6rem, 20vw, 16rem)' }} strokeWidth={1} />
      </div>

      <h3 className="font-semibold text-white mb-2 sm:mb-3" style={{ fontSize: 'clamp(1.5rem, 4vw, 4rem)' }}>
        {scene.label}
      </h3>

      <p className="fi-text mb-4 sm:mb-6" style={{ fontSize: 'clamp(0.875rem, 2vw, 2rem)' }}>
        {scene.subtitle}
      </p>

      <div className="flex items-center gap-3 text-slate-400 mt-auto">
        <div className="w-3 h-3 sm:w-4 sm:h-4 bg-white/30 rounded-full animate-ping" />
        <span style={{ fontSize: 'clamp(0.75rem, 1.5vw, 1.25rem)' }}>
          Respira profundo y relájate
        </span>
      </div>

      <div className="flex items-center gap-2 mt-4 sm:mt-6">
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
