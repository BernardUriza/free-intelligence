import { Download, ExternalLink, Gift } from 'lucide-react';

import type { Release } from '../types';
import { getDownloadUrl } from '../utils';

interface FinalCTASectionProps {
  loading: boolean;
  error: string | null;
  latestRelease: Release | undefined;
}

export function FinalCTASection({ loading, error, latestRelease }: FinalCTASectionProps) {
  return (
    <section className="dl-final-cta-section">
      <div className="dl-final-cta-content">
        {/* Urgency badge */}
        <div className="dl-section-badge-lg">
          <Gift className="dl-icon-sm" />
          Licencias Piloto Limitadas
        </div>

        <h2 className="dl-section-title">Sé parte de los primeros en usarlo</h2>
        <p className="dl-final-cta-subtitle">
          Estamos aceptando médicos para el programa piloto.
          <br className="dl-responsive-br" />
          Acceso gratuito a cambio de tu feedback.
        </p>

        {!loading && !error && (
          <a className="dl-cta-secondary" href={getDownloadUrl(latestRelease)} download>
            <Download className="dl-icon-cta-sm" />
            Obtener Mi Licencia Piloto
          </a>
        )}

        {/* Ollama requirement note */}
        <div className="dl-requirement-box">
          <p className="dl-requirement-text">
            <strong className="dl-strong-white">Requisito:</strong> Aurity Desktop usa{' '}
            <a
              href="https://ollama.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="dl-requirement-link"
            >
              Ollama <ExternalLink className="dl-icon-xs" />
            </a>{' '}
            para IA local. Instálalo primero, luego ejecuta{' '}
            <code className="dl-requirement-code">ollama pull qwen3:8b</code>
          </p>
        </div>
      </div>
    </section>
  );
}
