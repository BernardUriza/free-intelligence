/**
 * ClinicSelector
 *
 * Dropdown to select a clinic when user is superadmin or has access to multiple clinics.
 * Allows switching between clinics to view different contexts.
 *
 * Shared component for use in Dashboard TV, Medical AI, and other pages.
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Building2, Check } from 'lucide-react';
import type { Clinic } from '@/lib/api/clinics';

interface ClinicSelectorProps {
  clinics: Clinic[];
  selectedClinic: Clinic | null;
  onSelectClinic: (clinic: Clinic) => void;
  loading?: boolean;
  disabled?: boolean;
  /** Compact mode for smaller displays */
  compact?: boolean;
}

export function ClinicSelector({
  clinics,
  selectedClinic,
  onSelectClinic,
  loading = false,
  disabled = false,
  compact = false,
}: ClinicSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const displayName = selectedClinic?.name ?? 'Seleccionar clínica';

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled || loading}
        className={`
          flex items-center gap-2 rounded-lg border transition-all
          ${compact ? 'px-3 py-1.5 text-sm' : 'px-4 py-2'}
          ${disabled
            ? 'bg-slate-800/50 border-slate-700 text-slate-500 cursor-not-allowed'
            : 'bg-slate-800 border-slate-700 hover:border-cyan-500 text-white cursor-pointer'
          }
        `}
      >
        <Building2 className={compact ? 'w-3 h-3 text-cyan-400' : 'w-4 h-4 text-cyan-400'} />
        <span className="font-medium truncate max-w-[150px]">{displayName}</span>
        {loading ? (
          <div className={`${compact ? 'w-3 h-3' : 'w-4 h-4'} border-2 border-cyan-500 border-t-transparent rounded-full animate-spin`} />
        ) : (
          <ChevronDown className={`${compact ? 'w-3 h-3' : 'w-4 h-4'} transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        )}
      </button>

      {/* Dropdown Menu */}
      {isOpen && !disabled && (
        <div className="ui-dropdown-panel">
          <div className="p-2 border-b border-slate-700">
            <p className="text-xs text-slate-400 font-medium uppercase tracking-wide">
              Clínicas disponibles
            </p>
          </div>

          <div className="max-h-64 overflow-y-auto">
            {clinics.length === 0 ? (
              <div className="p-4 text-center text-slate-500 text-sm">
                No hay clínicas disponibles
              </div>
            ) : (
              clinics.map((clinic) => {
                const isSelected = selectedClinic?.clinic_id === clinic.clinic_id;

                return (
                  <button
                    key={clinic.clinic_id}
                    onClick={() => {
                      onSelectClinic(clinic);
                      setIsOpen(false);
                    }}
                    className={`
                      w-full flex items-center gap-3 px-3 py-2 text-left transition-colors
                      ${isSelected
                        ? 'bg-cyan-500/20 text-white'
                        : 'hover:bg-slate-700/50 text-slate-300'
                      }
                    `}
                  >
                    <div className={`
                      w-8 h-8 rounded-full flex items-center justify-center
                      ${isSelected ? 'bg-cyan-500/30' : 'bg-slate-700'}
                    `}>
                      <Building2 className="w-4 h-4 text-cyan-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{clinic.name}</p>
                      {clinic.specialty && (
                        <p className="text-xs text-slate-400 truncate">{clinic.specialty}</p>
                      )}
                    </div>
                    {isSelected && (
                      <Check className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
