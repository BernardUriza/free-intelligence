
import React from 'react';
import { Keyboard, X } from "lucide-react"
import { KEYBOARD_SHORTCUTS } from "@/lib/dashboard/constants"
import { formatShortcutKey } from "@/hooks/useDashboardShortcuts"

export const ShortcutsDisplay = ({ onClose }: { onClose: () => void }) => (
  <div className="absolute top-16 right-4 z-50 p-4 bg-slate-800/95 backdrop-blur-sm border border-slate-700 rounded-xl shadow-2xl w-80">
    <div className="flex items-center justify-between mb-3">
      <h3 className="fi-title-sm-medium flex items-center gap-2">
        <Keyboard className="w-4 h-4 fi-text-purple" />
        Atajos de Teclado
      </h3>
      <button onClick={onClose} className="text-slate-400 hover:text-white">
        <X className="w-4 h-4" />
      </button>
    </div>
    <div className="grid grid-cols-1 gap-2 text-xs">
      {Object.entries(KEYBOARD_SHORTCUTS).map(([key, shortcut]) => (
        <div key={key} className="flex items-center justify-between py-1">
          <span className="text-slate-400">{shortcut.description}</span>
          <kbd className="px-2 py-0.5 bg-slate-900 border border-slate-600 rounded fi-text font-mono">
            {formatShortcutKey(shortcut)}
          </kbd>
        </div>
      ))}
    </div>
  </div>
);
