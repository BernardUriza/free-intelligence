'use client';

/**
 * TimelineToolbar Component
 * 
 * Top toolbar for timeline scheduler with:
 * - View mode selector (day/week/month)
 * - Date navigation
 * - Zoom controls
 * - Quick actions (today, jump to latest)
 */

import React from 'react';
import { Button } from '@/components/ui/button';
import {
  ChevronLeft,
  ChevronRight,
  PanelLeftOpen,
  PanelLeftClose,
  ZoomIn,
  ZoomOut,
  ArrowRight,
} from 'lucide-react';
import { VIEW_PRESETS, formatDateForView, type ViewMode } from '@/components/bryntum';

interface TimelineToolbarProps {
  viewMode: ViewMode;
  currentDate: Date;
  zoomLevel: number;
  drawerOpen: boolean;
  onToggleDrawer: () => void;
  onViewModeChange: (mode: ViewMode) => void;
  onNavigateDate: (direction: 'prev' | 'next') => void;
  onGoToToday: () => void;
  onZoom: (direction: 'in' | 'out') => void;
  onJumpToLatest?: () => void;
}

export function TimelineToolbar({
  viewMode,
  currentDate,
  zoomLevel,
  drawerOpen,
  onToggleDrawer,
  onViewModeChange,
  onNavigateDate,
  onGoToToday,
  onZoom,
  onJumpToLatest,
}: TimelineToolbarProps) {
  const dateText = formatDateForView(viewMode, currentDate);
  const viewModes = Object.keys(VIEW_PRESETS) as ViewMode[];

  return (
    <div className="flex items-center justify-between p-3 bg-slate-900/50 fi-border-bottom">
      {/* Left: Drawer Toggle + View Mode */}
      <div className="fi-flex-gap">
        {/* Drawer Toggle */}
        <Button
          onClick={onToggleDrawer}
          className={`p-2 rounded-lg transition-colors ${
            drawerOpen
              ? 'bg-emerald-600 text-white'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
          variant="ghost"
          size="sm"
          title="Navegar"
        >
          {drawerOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
        </Button>

        {/* View Mode Selector */}
        <div className="flex items-center bg-slate-800 rounded-lg p-0.5">
          {viewModes.map((mode) => {
            const config = VIEW_PRESETS[mode];
            const Icon = config.icon;
            const isActive = viewMode === mode;
            return (
              <Button
                key={mode}
                onClick={() => onViewModeChange(mode)}
                className={`flex items-center gap-1 px-2 py-1 rounded fi-text-xs-medium transition-colors ${
                  isActive
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                }`}
                variant="ghost"
                size="sm"
                title={config.label}
              >
                <Icon className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">{config.label}</span>
              </Button>
            );
          })}
        </div>
      </div>

      {/* Center: Date Navigation */}
      <div className="flex items-center gap-1 bg-slate-800 rounded-lg p-0.5">
        <Button onClick={() => onNavigateDate('prev')} className="p-1.5 hover:bg-slate-700 rounded text-slate-400 hover:text-slate-200" variant="ghost" size="sm" title="Anterior">
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <Button onClick={onGoToToday} className="px-2 py-1 fi-text-xs-medium hover:bg-slate-700 rounded fi-text" variant="ghost" size="sm" title="Hoy">Hoy</Button>
        <span className="px-2 py-1 fi-text-xs-medium min-w-[120px] text-center text-slate-200">
          {dateText}
        </span>
        <Button onClick={() => onNavigateDate('next')} className="p-1.5 hover:bg-slate-700 rounded text-slate-400 hover:text-slate-200" variant="ghost" size="sm" title="Siguiente">
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Right: Zoom + Jump to Latest */}
      <div className="fi-flex-gap">
        {/* Zoom Controls */}
        <div className="flex items-center bg-slate-800 rounded-lg p-0.5">
          <Button
            onClick={() => onZoom('out')}
            disabled={zoomLevel <= 0.5}
            className="p-1.5 hover:bg-slate-700 rounded text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed"
            title="Alejar"
            variant="ghost"
            size="sm"
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          <span className="px-2 fi-text-xs min-w-[40px] text-center">
            {Math.round(zoomLevel * 100)}%
          </span>
          <Button
            onClick={() => onZoom('in')}
            disabled={zoomLevel >= 2}
            className="p-1.5 hover:bg-slate-700 rounded text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed"
            title="Acercar"
            variant="ghost"
            size="sm"
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
        </div>

        {/* Jump to Latest Event */}
        {onJumpToLatest && (
          <Button
            onClick={onJumpToLatest}
            className="flex items-center gap-1.5 px-2 py-1.5 fi-text-xs-medium fi-text hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
            title="Ir al último evento"
            variant="ghost"
            size="sm"
          >
            <ArrowRight className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Último</span>
          </Button>
        )}

        {/* Event Legend */}
        <div className="hidden md:flex items-center gap-4 text-xs ml-2">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-500" />
            <span className="text-slate-400">Usuario</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-violet-500" />
            <span className="text-slate-400">Asistente</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span className="text-slate-400">Audio</span>
          </div>
        </div>
      </div>
    </div>
  );
}
