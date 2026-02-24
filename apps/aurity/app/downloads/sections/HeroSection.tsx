import Image from 'next/image';
import { Download, RefreshCw, WifiOff, Lock, Gift } from 'lucide-react';
import { Button } from '@/components/ui/button';

import type { Release } from '../types';
import { getDownloadUrl } from '../utils';

interface HeroSectionProps {
  loading: boolean;
  error: string | null;
  latestRelease: Release | undefined;
  onRetry: () => void;
}

export function HeroSection({ loading, error, latestRelease, onRetry }: HeroSectionProps) {
  return (
    <section className="dl-hero">
      <div className="dl-hero-content">
        {/* Hero Wordmark */}
        <div className="dl-hero-wordmark">
          <Image
            src="/logos/aurity-logo-light.png"
            alt="AURITY"
            width={140}
            height={37}
            className="dl-hero-logo"
          />
        </div>

        {/* Headline */}
        <h1 className="dl-hero-title">El Copiloto Médico que Vive en Tu Computadora</h1>

        {/* Subheadline */}
        <p className="dl-hero-subtitle">
          Genera notas SOAP en segundos. 100% offline.
          <br className="dl-responsive-br" />
          <span className="dl-hero-accent">
            Ningún paciente en la nube. Ninguna suscripción mensual.
          </span>
        </p>

        {/* Trust badges */}
        <div className="dl-trust-badges">
          <div className="dl-trust-badge">
            <WifiOff className="dl-trust-icon" />
            <span>Funciona sin internet</span>
          </div>
          <div className="dl-trust-badge">
            <Lock className="dl-trust-icon" />
            <span>Tus datos nunca salen de tu PC</span>
          </div>
          <div className="dl-trust-badge">
            <Gift className="dl-trust-icon" />
            <span>Licencias piloto gratuitas</span>
          </div>
        </div>

        {/* CTA */}
        {loading ? (
          <div className="dl-loading">
            <RefreshCw className="dl-loading-icon" />
          </div>
        ) : error ? (
          <div className="dl-error">
            <p className="dl-error-text">{error}</p>
            <Button onClick={onRetry} variant="outline" className="dl-retry-btn">
              <RefreshCw className="dl-icon-refresh" />
              Reintentar
            </Button>
          </div>
        ) : (
          <div className="dl-cta-container">
            <a className="dl-cta-primary" href={getDownloadUrl(latestRelease)} download>
              <Download className="dl-icon-cta" />
              Descargar Gratis
            </a>
            {latestRelease && (
              <p className="dl-version-text">
                Versión {latestRelease.version} · macOS, Windows y Linux
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
