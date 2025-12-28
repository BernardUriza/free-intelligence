'use client';

/**
 * MicrophoneDevicePicker Component
 *
 * Compact dropdown for selecting audio input devices.
 * Appears as a small settings icon near the VoiceMicButton.
 *
 * Features:
 * - Lists available microphones
 * - Shows checkmark on selected device
 * - "Default" badge on system default device
 * - Loading spinner during enumeration
 * - Empty state when no devices detected
 * - Error state with permission request button
 *
 * Accessibility:
 * - Keyboard navigable
 * - ARIA labels for screen readers
 * - Focus management
 */

import { useState, useRef, useEffect } from 'react';
import { Settings2, Mic, Check, RefreshCw, AlertCircle, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { AudioDevice, PermissionState } from '@/hooks/useAudioDevices';

// =============================================================================
// Types
// =============================================================================

export interface MicrophoneDevicePickerProps {
  /** List of available audio input devices */
  devices: AudioDevice[];
  /** Currently selected device ID (null = system default) */
  selectedDeviceId: string | null;
  /** Loading state during device enumeration */
  isLoading: boolean;
  /** Error message if enumeration failed */
  error: string | null;
  /** Current microphone permission state */
  permissionState: PermissionState;
  /** Callback when device is selected */
  onDeviceSelect: (deviceId: string | null) => void;
  /** Callback to refresh device list */
  onRefresh: () => void;
  /** Callback to request microphone permission */
  onRequestPermission: () => void;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function MicrophoneDevicePicker({
  devices,
  selectedDeviceId,
  isLoading,
  error,
  permissionState,
  onDeviceSelect,
  onRefresh,
  onRequestPermission,
  className = '',
}: MicrophoneDevicePickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
        buttonRef.current?.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  const handleDeviceClick = (deviceId: string | null) => {
    onDeviceSelect(deviceId);
    setIsOpen(false);
  };

  return (
    <div className={`relative ${className}`}>
      {/* Trigger Button */}
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        className="fi-icon-btn-compact"
        title="Configurar micrófono"
        aria-label="Configurar dispositivo de audio"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <Settings2 className="w-3.5 h-3.5" />
      </button>

      {/* Dropdown Menu */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
              aria-hidden="true"
            />

            {/* Menu */}
            <motion.div
              ref={menuRef}
              initial={{ opacity: 0, y: 4, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 4, scale: 0.95 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
              className="
                absolute bottom-full right-0 mb-2 z-50
                w-64
                bg-slate-800/98 backdrop-blur-md border border-slate-700/80
                rounded-lg shadow-2xl
                overflow-hidden
              "
              role="listbox"
              aria-label="Seleccionar micrófono"
            >
              {/* Header */}
              <div className="px-3 py-2 bg-slate-900/50 fi-border-bottom/50">
                <div className="fi-flex-between">
                  <div className="fi-flex-gap">
                    <Mic className="w-3.5 h-3.5 fi-text-purple" />
                    <span className="text-xs font-semibold text-white">Micrófono</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onRefresh();
                    }}
                    className="p-1 rounded fi-hover-ghost"
                    title="Actualizar dispositivos"
                    aria-label="Actualizar lista de dispositivos"
                  >
                    <RefreshCw className={`fi-icon-xs ${isLoading ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              </div>

              {/* Content */}
              <div className="max-h-48 overflow-y-auto py-1">
                {/* Loading State */}
                {isLoading && (
                  <div className="flex items-center justify-center gap-2 py-4 text-slate-400">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-xs">Buscando dispositivos...</span>
                  </div>
                )}

                {/* Error State */}
                {!isLoading && error && (
                  <div className="px-3 py-3 text-center">
                    <AlertCircle className="w-5 h-5 fi-text-error mx-auto mb-2" />
                    <p className="text-xs text-red-300 mb-2">{error}</p>
                    {permissionState === 'denied' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onRequestPermission();
                        }}
                        className="text-xs fi-text-purple hover:text-purple-300 underline"
                      >
                        Solicitar permiso
                      </button>
                    )}
                  </div>
                )}

                {/* Permission Prompt State */}
                {!isLoading && !error && permissionState === 'prompt' && devices.length === 0 && (
                  <div className="px-3 py-3 text-center">
                    <Mic className="w-5 h-5 text-slate-400 mx-auto mb-2" />
                    <p className="fi-text-xs mb-2">
                      Permite acceso al micrófono para ver dispositivos
                    </p>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onRequestPermission();
                      }}
                      className="
                        px-3 py-1.5 rounded-md text-xs
                        bg-purple-600 hover:bg-purple-500 text-white
                        transition-colors
                      "
                    >
                      Permitir acceso
                    </button>
                  </div>
                )}

                {/* Empty State */}
                {!isLoading && !error && permissionState !== 'prompt' && devices.length === 0 && (
                  <div className="px-3 py-4 text-center">
                    <AlertCircle className="w-5 h-5 fi-text-warning mx-auto mb-2" />
                    <p className="fi-text-xs">
                      No se detectaron micrófonos
                    </p>
                    <p className="text-[10px] text-slate-500 mt-1">
                      Conecta un micrófono y actualiza
                    </p>
                  </div>
                )}

                {/* Device List */}
                {!isLoading && !error && devices.length > 0 && (
                  <>
                    {/* System Default Option */}
                    <button
                      onClick={() => handleDeviceClick(null)}
                      className={selectedDeviceId === null ? 'fi-select-option-selected' : 'fi-select-option'}
                      role="option"
                      aria-selected={selectedDeviceId === null}
                    >
                      <div className="w-4 h-4 flex items-center justify-center">
                        {selectedDeviceId === null && (
                          <Check className="w-3.5 h-3.5 fi-text-purple" />
                        )}
                      </div>
                      <span className="flex-1 truncate">Predeterminado del sistema</span>
                    </button>

                    {/* Separator */}
                    <div className="h-px bg-slate-700/50 my-1" />

                    {/* Device Options */}
                    {devices.map((device) => (
                      <button
                        key={device.deviceId}
                        onClick={() => handleDeviceClick(device.deviceId)}
                        className={selectedDeviceId === device.deviceId ? 'fi-select-option-selected' : 'fi-select-option'}
                        role="option"
                        aria-selected={selectedDeviceId === device.deviceId}
                      >
                        <div className="w-4 h-4 flex items-center justify-center">
                          {selectedDeviceId === device.deviceId && (
                            <Check className="w-3.5 h-3.5 fi-text-purple" />
                          )}
                        </div>
                        <span className="flex-1 truncate">{device.label}</span>
                        {device.isDefault && (
                          <span className="text-[10px] text-slate-500 px-1.5 py-0.5 bg-slate-700/50 rounded">
                            Default
                          </span>
                        )}
                      </button>
                    ))}
                  </>
                )}
              </div>

              {/* Footer */}
              <div className="fi-footer-disclaimer fi-border-top/50">
                <p className="fi-text-disclaimer">
                  {devices.length > 0
                    ? `${devices.length} dispositivo${devices.length !== 1 ? 's' : ''} disponible${devices.length !== 1 ? 's' : ''}`
                    : 'Conecta un micrófono para grabar'
                  }
                </p>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
