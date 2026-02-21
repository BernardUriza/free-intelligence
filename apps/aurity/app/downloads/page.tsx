/**
 * Downloads Page - Landing Page Optimizada
 *
 * Composition root — wires useReleases hook with section components.
 * Hidden in desktop mode (TauriInstalledView).
 */

'use client';

import Image from 'next/image';
import Link from 'next/link';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { detectTauri, isBrowser } from '@/lib/environment';
import { getBackendUrl } from '@/lib/api/client';
import { NeuralNetworkCanvas } from '@/components/background/NeuralNetworkCanvas';

import { useReleases } from './hooks/useReleases';
import { TauriInstalledView } from './components/TauriInstalledView';
import { MedicalAIDemo } from './components/MedicalAIDemo';
import { HeroSection } from './sections/HeroSection';
import { PhilosophySection } from './sections/PhilosophySection';
import { BenefitsSection } from './sections/BenefitsSection';
import { PlatformsSection } from './sections/PlatformsSection';
import { FAQSection } from './sections/FAQSection';
import { FinalCTASection } from './sections/FinalCTASection';

export default function DownloadsPage() {
  const isTauri = isBrowser() && detectTauri();
  const { latestRelease, loading, error, retry } = useReleases(isTauri);

  if (isTauri) {
    return <TauriInstalledView />;
  }

  return (
    <AppTemplate backgroundGradient="none" maxWidth="none" padding="0" showWatermark={true}>
      {/* Fixed Navbar Logo */}
      <nav className="dl-nav">
        <Link href="/" className="dl-nav-link" aria-label="Volver al hub de AURITY">
          <Image
            src="/logos/aurity-logo-light.png"
            alt="AURITY"
            width={96}
            height={26}
            className="dl-nav-logo"
            priority
          />
        </Link>
      </nav>

      <NeuralNetworkCanvas opacity={0.25} />

      <div className="dl-page">
        <HeroSection
          loading={loading}
          error={error}
          latestRelease={latestRelease}
          onRetry={retry}
        />

        <section className="dl-demo-section">
          <div className="dl-section-container">
            <MedicalAIDemo />
          </div>
        </section>

        <PhilosophySection />
        <BenefitsSection />

        {!loading && !error && latestRelease && (
          <PlatformsSection latestRelease={latestRelease} />
        )}

        <FAQSection />

        <FinalCTASection loading={loading} error={error} latestRelease={latestRelease} />

        <footer className="dl-footer">
          <p className="dl-footer-text">Aurity Desktop · Privacidad primero, siempre.</p>
        </footer>
      </div>
    </AppTemplate>
  );
}
