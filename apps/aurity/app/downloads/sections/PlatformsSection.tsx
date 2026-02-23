import { Download, Apple, Monitor, Tag, Cpu } from 'lucide-react';

import type { Release } from '../types';

interface PlatformsSectionProps {
  latestRelease: Release;
}

export function PlatformsSection({ latestRelease }: PlatformsSectionProps) {
  return (
    <section className="dl-platforms-section">
      <div className="dl-section-container-wide">
        {/* Version badges */}
        <div className="dl-version-badges">
          <span className="dl-version-badge dl-version-badge--aurity">
            <Tag className="dl-version-badge-icon" />
            Aurity Desktop v{latestRelease.version}
          </span>
          {latestRelease.fiVersion && (
            <span className="dl-version-badge dl-version-badge--fi">
              <Cpu className="dl-version-badge-icon" />
              FI Monitor v{latestRelease.fiVersion}
            </span>
          )}
        </div>

        <h2 className="dl-platforms-title">Disponible para tu plataforma</h2>
        <p className="dl-platforms-subtitle">Instalación simple, sin configuración complicada</p>

        <div className="dl-platforms-grid">
          {/* macOS */}
          <div className="dl-platform-card">
            <div className="dl-platform-header">
              <div className="dl-platform-icon-box">
                <Apple className="dl-platform-icon" />
              </div>
              <div>
                <h3 className="dl-platform-name">macOS</h3>
                <p className="dl-platform-desc">Apple Silicon e Intel</p>
              </div>
            </div>
            {latestRelease.platforms.macos ? (
              <a
                className="dl-download-btn"
                href={
                  latestRelease.platforms.macos.url !== '#coming-soon'
                    ? latestRelease.platforms.macos.url
                    : undefined
                }
                download
              >
                <Download className="dl-icon-sm" />
                {latestRelease.platforms.macos.url === '#coming-soon'
                  ? 'Próximamente'
                  : 'Descargar DMG'}
              </a>
            ) : (
              <p className="dl-platform-desc">Aún no disponible</p>
            )}
          </div>

          {/* Windows */}
          <div className="dl-platform-card">
            <div className="dl-platform-header">
              <div className="dl-platform-icon-box">
                <Monitor className="dl-platform-icon" />
              </div>
              <div>
                <h3 className="dl-platform-name">Windows</h3>
                <p className="dl-platform-desc">Windows 10/11 (64-bit)</p>
              </div>
            </div>
            {latestRelease.platforms.windows ? (
              <>
                <a
                  className="dl-download-btn"
                  href={
                    latestRelease.platforms.windows.url !== '#coming-soon'
                      ? latestRelease.platforms.windows.url
                      : undefined
                  }
                  download
                >
                  <Download className="dl-icon-sm" />
                  {latestRelease.platforms.windows.url === '#coming-soon'
                    ? 'Próximamente'
                    : 'Descargar EXE'}
                </a>
                <p
                  className="dl-platform-hint"
                  style={{
                    fontSize: '11px',
                    color: 'rgba(255,255,255,0.5)',
                    marginTop: '8px',
                    lineHeight: '1.4',
                  }}
                >
                  Si Windows SmartScreen bloquea la instalación, haz clic en &quot;Más
                  información&quot; &rarr; &quot;Ejecutar de todas formas&quot;. No se requieren
                  permisos de administrador.
                </p>
              </>
            ) : (
              <p className="dl-platform-desc">Aún no disponible</p>
            )}
          </div>

          {/* Linux */}
          <div className="dl-platform-card-wide">
            <div className="dl-platform-header">
              <div className="dl-platform-icon-box">
                <Monitor className="dl-platform-icon" />
              </div>
              <div>
                <h3 className="dl-platform-name">Linux</h3>
                <p className="dl-platform-desc">AppImage (x86_64)</p>
              </div>
            </div>
            {latestRelease.platforms.linux ? (
              <a
                className="dl-download-btn"
                href={
                  latestRelease.platforms.linux.url !== '#coming-soon'
                    ? latestRelease.platforms.linux.url
                    : undefined
                }
                download
              >
                <Download className="dl-icon-sm" />
                {latestRelease.platforms.linux.url === '#coming-soon'
                  ? 'Próximamente'
                  : 'Descargar AppImage'}
              </a>
            ) : (
              <p className="dl-platform-desc">Aún no disponible</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
