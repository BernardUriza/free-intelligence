'use client';

/**
 * KeyboardShortcutsBar Component
 * 
 * Bottom bar displaying available keyboard shortcuts for quick reference.
 */

import React from 'react';

export function KeyboardShortcutsBar() {
  return (
    <div className="px-3 py-2 bg-slate-900/30 border-t border-slate-800 fi-text-xs-muted flex items-center gap-4">
      <span>
        <kbd className="px-1 py-0.5 bg-slate-800 rounded text-slate-400">Shift</kbd>+
        <kbd className="px-1 py-0.5 bg-slate-800 rounded text-slate-400">←/→</kbd> Navegar
      </span>
      <span>
        <kbd className="px-1 py-0.5 bg-slate-800 rounded text-slate-400">+/-</kbd> Zoom
      </span>
      <span>
        <kbd className="px-1 py-0.5 bg-slate-800 rounded text-slate-400">T</kbd> Hoy
      </span>
      <span>
        <kbd className="px-1 py-0.5 bg-slate-800 rounded text-slate-400">Esc</kbd> Cerrar
      </span>
    </div>
  );
}
