'use client';

import { useState } from 'react';
import { Video } from 'lucide-react';

interface ClinicVideoWidgetProps {
  videoUrl: string;
  title?: string;
  description?: string;
}

export function ClinicVideoWidget({ videoUrl, title, description }: ClinicVideoWidgetProps) {
  const [hasError, setHasError] = useState(false);

  if (hasError) {
    return (
      <div className="bg-gradient-to-br from-slate-950/80 to-slate-900/80 border border-slate-700 rounded-xl overflow-hidden backdrop-blur-sm h-80 flex items-center justify-center">
        <div className="text-center p-6">
          <Video className="w-12 h-12 text-slate-400 mx-auto mb-4" strokeWidth={1.5} aria-hidden="true" />
          <p className="text-slate-400">Video no disponible</p>
          {title && <p className="text-slate-500 text-sm mt-2">{title}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-slate-950/80 to-slate-900/80 border border-slate-700 rounded-xl overflow-hidden backdrop-blur-sm">
      <div className="relative w-full h-80 bg-slate-900">
        <video
          src={videoUrl}
          className="w-full h-full object-contain"
          autoPlay
          muted
          loop
          playsInline
          onError={() => setHasError(true)}
        />
      </div>

      {(title || description) && (
        <div className="p-6 fi-border-top/50">
          {title && <h3 className="text-lg font-bold text-white mb-2">{title}</h3>}
          {description && <p className="text-sm fi-text leading-relaxed">{description}</p>}
          <div className="mt-3 fi-flex-gap fi-text-xs-muted">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z" />
            </svg>
            <span>Contenido de su clínica</span>
          </div>
        </div>
      )}
    </div>
  );
}
