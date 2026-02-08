'use client';

import { useState } from 'react';
import { Camera } from 'lucide-react';

interface ClinicImageWidgetProps {
  imageUrl: string;
  title?: string;
  description?: string;
}

export function ClinicImageWidget({ imageUrl, title, description }: ClinicImageWidgetProps) {
  const [hasError, setHasError] = useState(false);

  if (hasError) {
    return (
      <div className="wgt-media-error">
        <div className="text-center p-6">
          <Camera className="w-12 h-12 text-slate-400 mx-auto mb-4" strokeWidth={1.5} aria-hidden="true" />
          <p className="text-slate-400">Imagen no disponible</p>
          {title && <p className="text-slate-500 text-sm mt-2">{title}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="wgt-media-card">
      <div className="relative w-full h-80 bg-slate-900">
        <img
          src={imageUrl}
          alt={title || 'Clinic image'}
          className="w-full h-full object-contain"
          onError={() => setHasError(true)}
          loading="lazy"
        />
      </div>

      {(title || description) && (
        <div className="p-6 fi-border-top/50">
          {title && <h3 className="text-lg font-bold text-white mb-2">{title}</h3>}
          {description && <p className="text-sm fi-text leading-relaxed">{description}</p>}
          <div className="mt-3 fi-flex-gap fi-text-xs-muted">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M13 7H7v6h6V7z" />
              <path fillRule="evenodd" d="M7 2a1 1 0 012 0v1h2V2a1 1 0 112 0v1h2a2 2 0 012 2v2h1a1 1 0 110 2h-1v2h1a1 1 0 110 2h-1v2a2 2 0 01-2 2h-2v1a1 1 0 11-2 0v-1H9v1a1 1 0 11-2 0v-1H5a2 2 0 01-2-2v-2H2a1 1 0 110-2h1V9H2a1 1 0 010-2h1V5a2 2 0 012-2h2V2zM5 5h10v10H5V5z" clipRule="evenodd" />
            </svg>
            <span>Contenido de su clínica</span>
          </div>
        </div>
      )}
    </div>
  );
}
