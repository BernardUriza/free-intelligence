
import React from 'react';
import Link from "next/link"
import Image from "next/image"
import {
  Users,
  Clock,
  Calendar,
  Keyboard,
  PanelLeftClose,
  PanelLeft,
  Tv,
  ExternalLink,
} from "lucide-react"
import { ShortcutsDisplay } from './ShortcutsDisplay';
import { UserDisplay } from "@/components/auth/UserDisplay";

export const DashboardHeader = ({
  waitingCount,
  avgWaitTime,
  showSidePanel,
  setShowSidePanel,
  setSidePanelTab,
  showShortcuts,
  setShowShortcuts,
}: any) => (
  <header className="flex-shrink-0 px-4 py-3">
    <div className="fi-flex-between">
      <div className="fi-flex-gap-lg">
        <Link href="/" className="fi-flex-gap">
          <Image src="/logos/aurity-logo-light.png" alt="Aurity" width={100} height={28} loading="eager" className="h-7 w-auto opacity-90" style={{ height: 'auto' }} />
        </Link>
        <div className="dash-live-badge">
          <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
          <span className="fi-text-xs-medium fi-text-success">EN VIVO</span>
        </div>
      </div>
      <div className="hidden md:fi-flex-gap">
        <button
          onClick={() => { setShowSidePanel(true); setSidePanelTab('queue'); }}
          className="dash-stat-btn"
        >
          <Users className="w-4 h-4 fi-text-primary" />
          <span className="fi-title-sm-medium">{waitingCount}</span>
          <span className="fi-text-xs">en espera</span>
        </button>
        <div className="fi-flex-gap px-3 py-1.5 bg-slate-800/80 border border-slate-700 rounded-lg">
          <Clock className="w-4 h-4 fi-text-warning" />
          <span className="fi-title-sm-medium">{avgWaitTime}</span>
          <span className="fi-text-xs">min</span>
        </div>
        <div className="fi-flex-gap px-3 py-1.5 bg-slate-800/80 border border-slate-700 rounded-lg">
          <Calendar className="w-4 h-4 fi-text-success" />
          <span className="fi-title-sm-medium">12</span>
          <span className="fi-text-xs">citas hoy</span>
        </div>
      </div>
      <div className="fi-flex-gap">
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
          className="dash-tv-mode-btn"
        >
          <Tv className="w-4 h-4" />
          <span className="hidden sm:inline">Abrir TV</span>
          <ExternalLink className="w-3.5 h-3.5 opacity-70" />
        </Link>
        <UserDisplay />
      </div>
    </div>
    {showShortcuts && <ShortcutsDisplay onClose={() => setShowShortcuts(false)} />}
  </header>
);
