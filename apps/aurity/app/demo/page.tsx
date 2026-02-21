/**
 * Demo Data Loader Page
 * Card: FI-UI-FEAT-207
 *
 * Composition root — wires useDemoData hook with presentational components.
 */

'use client';

import { Info } from 'lucide-react';
import { AppTemplate } from '@/components/layout/AppTemplate';

import { useDemoData } from './hooks/useDemoData';
import { StatusMessage } from './components/StatusMessage';
import { DemoActions } from './components/DemoActions';
import { SessionsList } from './components/SessionsList';
import { DeepLinksGrid } from './components/DeepLinksGrid';
import { QuickStartGuide } from './components/QuickStartGuide';

export default function DemoPage() {
  const {
    isLoaded,
    sessions,
    isLoading,
    showConfirm,
    message,
    setShowConfirm,
    handleLoadDemo,
    handleResetDemo,
  } = useDemoData();

  return (
    <AppTemplate
      headerConfig={{
        title: 'Demo Dataset',
        subtitle: 'Load sample data to explore all features',
        icon: 'database',
        iconColor: 'fi-text-purple',
        showBackButton: true,
      }}
      maxWidth="5xl"
      padding="0"
      showWatermark={true}
      showGeometricBg={true}
    >
      <div className="demo-page">
        {/* Info Banner */}
        <div className="demo-info-banner">
          <div className="demo-info-banner-row">
            <Info className="demo-info-banner-icon" />
            <div>
              <p className="demo-info-banner-title">Demo Mode</p>
              <p className="demo-info-banner-text">
                Load a sample dataset to explore the application without affecting production data.
                Demo data includes 3 sessions (medical, legal, code) with 8-12 events each.
              </p>
            </div>
          </div>
        </div>

        {message && <StatusMessage message={message} />}

        <DemoActions
          isLoaded={isLoaded}
          isLoading={isLoading}
          showConfirm={showConfirm}
          onShowConfirm={setShowConfirm}
          onLoadDemo={handleLoadDemo}
          onResetDemo={handleResetDemo}
        />

        {isLoaded && <SessionsList sessions={sessions} />}

        <DeepLinksGrid />

        <QuickStartGuide />
      </div>
    </AppTemplate>
  );
}
