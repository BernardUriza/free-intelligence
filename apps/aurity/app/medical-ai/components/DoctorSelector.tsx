/**
 * DoctorSelector
 *
 * Dropdown to select a doctor when user has clinic admin privileges.
 * Shows current doctor's name and allows switching to view other doctors' calendars.
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { ChevronDown, User, Stethoscope, Check } from 'lucide-react';
import type { Doctor } from '@/lib/api/clinics';

interface DoctorSelectorProps {
  doctors: Doctor[];
  selectedDoctor: Doctor | null;
  onSelectDoctor: (doctor: Doctor) => void;
  loading?: boolean;
  disabled?: boolean;
}

export function DoctorSelector({
  doctors,
  selectedDoctor,
  onSelectDoctor,
  loading = false,
  disabled = false,
}: DoctorSelectorProps) {
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

  const displayName = selectedDoctor
    ? selectedDoctor.display_name || `${selectedDoctor.nombre} ${selectedDoctor.apellido}`
    : 'Seleccionar doctor';

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled || loading}
        className={`ui-dropdown-trigger ${disabled
            ? 'bg-slate-800/50 border-slate-700 text-slate-500 cursor-not-allowed'
            : 'bg-slate-800 border-slate-700 hover:border-indigo-500 text-white cursor-pointer'
          }`}
      >
        <Stethoscope className="w-4 h-4 text-indigo-400" />
        <span className="font-medium">{displayName}</span>
        {loading ? (
          <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        ) : (
          <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        )}
      </button>

      {/* Dropdown Menu */}
      {isOpen && !disabled && (
        <div className="ui-dropdown-panel">
          <div className="ui-dropdown-header">
            <p className="ui-dropdown-header-text">
              Doctores de la clínica
            </p>
          </div>

          <div className="max-h-64 overflow-y-auto">
            {doctors.length === 0 ? (
              <div className="ui-dropdown-empty">
                No hay doctores disponibles
              </div>
            ) : (
              doctors.map((doctor) => {
                const name = doctor.display_name || `${doctor.nombre} ${doctor.apellido}`;
                const isSelected = selectedDoctor?.doctor_id === doctor.doctor_id;

                return (
                  <button
                    key={doctor.doctor_id}
                    onClick={() => {
                      onSelectDoctor(doctor);
                      setIsOpen(false);
                    }}
                    className={`ui-dropdown-option ${isSelected
                        ? 'bg-indigo-500/20 text-white'
                        : 'hover:bg-slate-700/50 text-slate-300'
                      }`}
                  >
                    <div className={`ui-dropdown-avatar ${isSelected ? 'bg-indigo-500/30' : 'bg-slate-700'}`}>
                      <User className="w-4 h-4 text-indigo-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{name}</p>
                      {doctor.especialidad && (
                        <p className="text-xs text-slate-400 truncate">{doctor.especialidad}</p>
                      )}
                    </div>
                    {isSelected && (
                      <Check className="w-4 h-4 text-indigo-400 flex-shrink-0" />
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
