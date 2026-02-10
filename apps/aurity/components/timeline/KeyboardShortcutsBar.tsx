'use client';

/**
 * KeyboardShortcutsBar Component
 * 
 * Bottom bar displaying available keyboard shortcuts for quick reference.
 */

import React from 'react';

export function KeyboardShortcutsBar() {
  return (
    <div className="history-shortcuts-bar">
      <span>
        <kbd className="history-kbd">Shift</kbd>+
        <kbd className="history-kbd">←/→</kbd> Navegar
      </span>
      <span>
        <kbd className="history-kbd">+/-</kbd> Zoom
      </span>
      <span>
        <kbd className="history-kbd">T</kbd> Hoy
      </span>
      <span>
        <kbd className="history-kbd">Esc</kbd> Cerrar
      </span>
    </div>
  );
}
