
import React from 'react';
import {
  Play,
  Pause,
  ChevronLeft,
  ChevronRight,
  Bell,
  Layers,
  MessageSquare,
} from "lucide-react"

interface Patient {
  ticketNumber: string;
  status?: 'waiting' | 'in_progress' | string;
  estimatedWait?: number;
}

interface PlaybackControlsProps {
  isAutoPlaying: boolean;
  setIsAutoPlaying: (v: boolean | ((prev: boolean) => boolean)) => void;
  info: (msg: string) => void;
  setCarouselIndex: (idx: number | ((prev: number) => number)) => void;
  totalCarouselItems: number;
  firstWaitingPatient?: Patient | null;
  calledPatient?: Patient | null;
  handleCallNext: (ticketNumber: string) => void;
  setShowSidePanel: (show: boolean) => void;
  setSidePanelTab: (tab: 'queue' | 'content' | 'message') => void;
}

export const PlaybackControls: React.FC<PlaybackControlsProps> = ({
  isAutoPlaying,
  setIsAutoPlaying,
  info,
  setCarouselIndex,
  totalCarouselItems,
  firstWaitingPatient,
  calledPatient,
  handleCallNext,
  setShowSidePanel,
  setSidePanelTab,
}) => (
  <div className="flex-shrink-0 mt-3">
    <div className="cc-controls-bar">
      <div className="fi-flex-gap">
        <button
          onClick={() => {
            setIsAutoPlaying((prev: boolean) => !prev)
            info(isAutoPlaying ? 'Auto-play pausado' : 'Auto-play activado')
          }}
          className={`p-2.5 rounded-lg transition-colors ${
            isAutoPlaying
              ? 'bg-emerald-500/20 fi-text-success hover:bg-emerald-500/30'
              : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
          }`}
          title={isAutoPlaying ? 'Pausar (Space)' : 'Reproducir (Space)'}
        >
          {isAutoPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
        </button>
        <div className="w-px h-6 bg-slate-700" />
        <button
          onClick={() => setCarouselIndex((prev: number) => (prev - 1 + totalCarouselItems) % totalCarouselItems)}
          className="p-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          title="Anterior (←)"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <button
          onClick={() => setCarouselIndex((prev: number) => (prev + 1) % totalCarouselItems)}
          className="p-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          title="Siguiente (→)"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
      <div className="hidden sm:flex items-center gap-1.5">
        {Array.from({ length: Math.min(totalCarouselItems, 12) }).map((_, i) => (
          <button
            key={i}
            onClick={() => setCarouselIndex(i)}
            className={`w-2 h-2 rounded-full transition-all ${
              i === 0 ? 'bg-purple-500 w-4' : 'bg-slate-600 hover:bg-slate-500'
            }`}
            title={`Slide ${i + 1}`}
          />
        ))}
        {totalCarouselItems > 12 && (
          <span className="fi-text-xs-muted ml-1">+{totalCarouselItems - 12}</span>
        )}
      </div>
      <div className="fi-flex-gap">
        {firstWaitingPatient && !calledPatient && (
          <button
            onClick={() => handleCallNext(firstWaitingPatient.ticketNumber)}
            className="cc-call-btn"
          >
            <Bell className="w-4 h-4" />
            <span className="hidden sm:inline">Llamar</span>
            <span className="font-mono">{firstWaitingPatient.ticketNumber}</span>
          </button>
        )}
        <button
          onClick={() => { setShowSidePanel(true); setSidePanelTab('content'); }}
          className="cc-action-btn"
          title="Gestionar contenido"
        >
          <Layers className="w-5 h-5" />
        </button>
        <button
          onClick={() => { setShowSidePanel(true); setSidePanelTab('message'); }}
          className="cc-action-btn"
          title="Enviar mensaje"
        >
          <MessageSquare className="w-5 h-5" />
        </button>
      </div>
    </div>
  </div>
);
