'use client';

/**
 * NavigateDrawer Component
 * 
 * Side drawer for session filtering and navigation.
 * Shows:
 * - Event count stats (chat/audio)
 * - Session search
 * - Session list with selection
 */

import React from 'react';
import { Search, X, MessageCircle, Mic } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface NavigateDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  sessions: string[];
  selectedSession: string | null;
  onSessionSelect: (session: string | null) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  chatCount: number;
  audioCount: number;
}

export function NavigateDrawer({
  isOpen,
  onClose,
  sessions,
  selectedSession,
  onSessionSelect,
  searchQuery,
  onSearchChange,
  chatCount,
  audioCount,
}: NavigateDrawerProps) {
  if (!isOpen) return null;

  const filteredSessions = sessions.filter((s) =>
    s.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="w-72 bg-slate-900 border-r border-slate-700 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 fi-border-bottom flex items-center justify-between">
        <h3 className="fi-title-sm-medium">Navegar</h3>
        <Button
          onClick={onClose}
          variant="ghost"
          size="sm"
          icon={X}
          aria-label="Cerrar"
        />
      </div>

      {/* Stats */}
      <div className="p-4 fi-border-bottom grid grid-cols-2 gap-3">
        <div className="p-3 rounded-lg bg-sky-950/30 border border-sky-700/30">
          <div className="fi-flex-gap">
            <MessageCircle className="h-4 w-4 text-sky-400" />
            <span className="text-lg font-bold text-sky-400">{chatCount}</span>
          </div>
          <div className="fi-text-xs">Chat</div>
        </div>
        <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-700/30">
          <div className="fi-flex-gap">
            <Mic className="h-4 w-4 fi-text-success" />
            <span className="text-lg font-bold fi-text-success">{audioCount}</span>
          </div>
          <div className="fi-text-xs">Audio</div>
        </div>
      </div>

      {/* Search */}
      <div className="p-4 fi-border-bottom">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Buscar sesión..."
            className="fi-search-input-sm"
          />
        </div>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto p-2">
        <Button
          onClick={() => onSessionSelect(null)}
          className={`w-full px-3 py-2 rounded-lg text-left text-sm transition-colors ${
            selectedSession === null
              ? 'bg-emerald-600 text-white'
              : 'fi-text hover:bg-slate-800'
          }`}
          variant="ghost"
          size="sm"
          title="Todas las sesiones"
        >
          Todas las sesiones
        </Button>

        {filteredSessions.map((session) => (
          <Button
            key={session}
            onClick={() => onSessionSelect(session)}
            className={`w-full px-3 py-2 rounded-lg text-left text-sm transition-colors mt-1 ${
              selectedSession === session
                ? 'bg-emerald-600 text-white'
                : 'fi-text hover:bg-slate-800'
            }`}
            variant="ghost"
            size="sm"
            title={`Seleccionar sesión ${session.slice(0, 8)}`}
          >
            <div className="font-mono text-xs truncate">{session.slice(0, 16)}...</div>
          </Button>
        ))}

        {filteredSessions.length === 0 && (
          <p className="text-center text-sm text-slate-500 py-4">No hay sesiones</p>
        )}
      </div>
    </div>
  );
}
