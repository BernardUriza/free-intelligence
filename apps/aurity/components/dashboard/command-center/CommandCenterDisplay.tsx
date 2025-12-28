
import React from 'react';
import Link from 'next/link';
import { Tv, ExternalLink, PanelLeftClose, PanelLeft, Keyboard } from 'lucide-react';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { ToastContainer } from "@/components/ui/ToastContainer"
import { dashboardHeader } from '@/config/page-headers';
import { useCommandCenterState } from './useCommandCenterState';
import { ShortcutsDisplay } from './ShortcutsDisplay';
import { TVPreview } from './TVPreview';
import { PlaybackControls } from './PlaybackControls';
import { SidePanel } from './SidePanel';

export function CommandCenterDisplay() {
  const {
    doctorMessage, setDoctorMessage,
    slides,
    isLoadingSlides,
    carouselIndex, setCarouselIndex,
    totalCarouselItems,
    carouselContent,
    isAutoPlaying, setIsAutoPlaying,
    showSidePanel, setShowSidePanel,
    sidePanelTab, setSidePanelTab,
    showShortcuts, setShowShortcuts,
    toasts, removeToast, success, info,
    queuePatients,
    waitingCount,
    avgWaitTime,
    inProgressCount,
    handleCallNext,
    handleMarkComplete,
    firstWaitingPatient,
    calledPatient,
    handleIndexChange,
    handleContentLoad,
  } = useCommandCenterState()

  const headerConfig = dashboardHeader({
    waitingCount,
    avgWaitTime,
    appointmentsToday: 12, // TODO: Fetch from API
  });

  // Custom header actions for dashboard
  const headerActions = (
    <div className="fi-flex-gap">
      <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/30 rounded-full">
        <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
        <span className="fi-text-xs-medium fi-text-success">EN VIVO</span>
      </div>
      <button
        onClick={() => setShowShortcuts(!showShortcuts)}
        className="fi-icon-btn"
        title="Atajos de teclado"
      >
        <Keyboard className="w-4 h-4" />
      </button>
      <button
        onClick={() => setShowSidePanel(!showSidePanel)}
        className={showSidePanel ? 'fi-icon-btn-active' : 'fi-icon-btn'}
        title={showSidePanel ? 'Cerrar panel' : 'Abrir panel de control'}
      >
        {showSidePanel ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeft className="w-4 h-4" />}
      </button>
      <Link
        href="/dashboard?mode=tv"
        target="_blank"
        className="flex items-center gap-2 px-3 py-2 bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium rounded-lg transition-colors"
      >
        <Tv className="w-4 h-4" />
        <span className="hidden sm:inline">Abrir TV</span>
        <ExternalLink className="w-3.5 h-3.5 opacity-70" />
      </Link>
    </div>
  );

  return (
    <AppTemplate
      headerConfig={headerConfig}
      headerActions={headerActions}
      backgroundGradient="slate"
      padding="4"
      maxWidth="full"
      fullHeight={true}
    >
      <ToastContainer toasts={toasts} onRemove={removeToast} />
      {showShortcuts && <ShortcutsDisplay onClose={() => setShowShortcuts(false)} />}

      <div className="flex-1 flex gap-4 h-full overflow-hidden">
        <div className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ${showSidePanel ? 'lg:mr-0' : ''}`}>
          <TVPreview
            isLoadingSlides={isLoadingSlides}
            doctorMessage={doctorMessage}
            slides={slides}
            carouselIndex={carouselIndex}
            handleIndexChange={handleIndexChange}
            handleContentLoad={handleContentLoad}
            totalCarouselItems={totalCarouselItems}
            carouselContent={carouselContent}
            isAutoPlaying={isAutoPlaying}
            calledPatient={calledPatient}
            handleMarkComplete={handleMarkComplete}
          />

          <PlaybackControls
            isAutoPlaying={isAutoPlaying}
            setIsAutoPlaying={setIsAutoPlaying}
            info={info}
            setCarouselIndex={setCarouselIndex}
            totalCarouselItems={totalCarouselItems}
            firstWaitingPatient={firstWaitingPatient}
            calledPatient={calledPatient}
            handleCallNext={handleCallNext}
            setShowSidePanel={setShowSidePanel}
            setSidePanelTab={setSidePanelTab}
          />
        </div>

        {showSidePanel && (
          <SidePanel
            sidePanelTab={sidePanelTab}
            setSidePanelTab={setSidePanelTab}
            setShowSidePanel={setShowSidePanel}
            calledPatient={calledPatient}
            handleMarkComplete={handleMarkComplete}
            firstWaitingPatient={firstWaitingPatient}
            handleCallNext={handleCallNext}
            queuePatients={queuePatients}
            waitingCount={waitingCount}
            inProgressCount={inProgressCount}
            carouselContent={carouselContent}
            setDoctorMessage={setDoctorMessage}
            doctorMessage={doctorMessage ?? undefined}
            success={success}
          />
        )}
      </div>
    </AppTemplate>
  )
}
