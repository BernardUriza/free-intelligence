"use client";

/**
 * Patient Setup Form - Phase 5 (FI-ONBOARD-006)
 *
 * Interactive patient creation with real-time HDF5 preview
 */

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from '@/components/ui/button';
import { User, AlertTriangle, CheckCircle2, Timer, UserRound } from 'lucide-react';

export interface PatientFormData {
  nombre: string;
  edad: number | '';
  genero: 'masculino' | 'femenino' | 'otro' | '';
  motivoConsulta?: string;
}

interface PatientSetupFormProps {
  onDataChange: (data: PatientFormData) => void;
  onSkipDemo: () => void;
}

export function PatientSetupForm({ onDataChange, onSkipDemo }: PatientSetupFormProps) {
  const [formData, setFormData] = useState<PatientFormData>({
    nombre: '',
    edad: '',
    genero: '',
    motivoConsulta: '',
  });

  const [errors, setErrors] = useState<Partial<Record<keyof PatientFormData, string>>>({});
  const [touched, setTouched] = useState<Partial<Record<keyof PatientFormData, boolean>>>({});

  /**
   * Validate form field
   */
  const validateField = (name: keyof PatientFormData, value: string | number): string | null => {
    switch (name) {
      case 'nombre':
        if (!value || (typeof value === 'string' && value.trim().length === 0)) {
          return 'Nombre es requerido';
        }
        if (typeof value === 'string' && value.length < 2) {
          return 'Nombre debe tener al menos 2 caracteres';
        }
        return null;

      case 'edad':
        if (value === '' || value === null) {
          return 'Edad es requerida';
        }
        const edad = Number(value);
        if (isNaN(edad) || edad < 0 || edad > 120) {
          return 'Edad debe estar entre 0 y 120';
        }
        return null;

      case 'genero':
        if (!value || value === '') {
          return 'Género es requerido';
        }
        return null;

      default:
        return null;
    }
  };

  /**
   * Handle field change
   */
  const handleChange = (name: keyof PatientFormData, value: string | number) => {
    const newData = { ...formData, [name]: value };
    setFormData(newData);

    // Validate and update errors
    const error = validateField(name, value);
    setErrors(prev => ({ ...prev, [name]: error || undefined }));

    // Notify parent
    onDataChange(newData);
  };

  /**
   * Handle blur (mark field as touched)
   */
  const handleBlur = (name: keyof PatientFormData) => {
    setTouched(prev => ({ ...prev, [name]: true }));
  };

  /**
   * Check if form is valid
   */
  const isFormValid = () => {
    return (
      formData.nombre.trim().length >= 2 &&
      formData.edad !== '' &&
      Number(formData.edad) >= 0 &&
      Number(formData.edad) <= 120 &&
      formData.genero !== ''
    );
  };

  return (
    <div className="space-y-6">
      {/* Form Title */}
      <div className="p-4 bg-emerald-950/20 border border-emerald-700/30 rounded-xl">
        <p className="text-sm text-emerald-300 flex items-start gap-2">
          <User className="w-4 h-4 flex-shrink-0 mt-0.5" strokeWidth={1.5} aria-hidden="true" />
          <span><strong>Paciente Demo:</strong> Estos datos se guardarán localmente (LocalStorage) solo para esta demo.
          No se envían a ningún servidor.</span>
        </p>
      </div>

      {/* Nombre */}
      <div className="fi-stack-sm">
        <label htmlFor="nombre" className="block text-sm font-semibold text-slate-200">
          Nombre completo <span className="fi-text-error">*</span>
        </label>
        <Input
          id="nombre"
          type="text"
          value={formData.nombre}
          onChange={(e) => handleChange('nombre', e.target.value)}
          onBlur={() => handleBlur('nombre')}
          placeholder="Ej: Juan Pérez García"
          error={touched.nombre && !!errors.nombre}
          errorMessage={touched.nombre ? errors.nombre : undefined}
          className="px-4 py-3 bg-slate-900/60 border-2"
        />
        {touched.nombre && errors.nombre && (
          <p className="text-xs fi-text-error flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" strokeWidth={1.5} aria-hidden="true" />
            {errors.nombre}
          </p>
        )}
        {formData.nombre.length > 0 && !errors.nombre && (
          <p className="text-xs fi-text-success flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" strokeWidth={1.5} aria-hidden="true" />
            Nombre válido
          </p>
        )}
      </div>

      {/* Edad */}
      <div className="fi-stack-sm">
        <label htmlFor="edad" className="block text-sm font-semibold text-slate-200">
          Edad (años) <span className="fi-text-error">*</span>
        </label>
        <Input
          id="edad"
          type="number"
          min="0"
          max="120"
          value={formData.edad}
          onChange={(e) => handleChange('edad', e.target.value === '' ? '' : Number(e.target.value))}
          onBlur={() => handleBlur('edad')}
          placeholder="Ej: 35"
          className={`w-full px-4 py-3 bg-slate-900/60 border-2 rounded-xl text-slate-200 placeholder-slate-500 transition-all ${
            touched.edad && errors.edad
              ? 'border-red-500/50 focus:border-red-500'
              : 'border-slate-700/50 focus:border-emerald-500'
          } focus:outline-none focus:ring-2 focus:ring-emerald-500/20`}
        />
        {touched.edad && errors.edad && (
          <p className="text-xs fi-text-error flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" strokeWidth={1.5} aria-hidden="true" />
            {errors.edad}
          </p>
        )}
        {formData.edad !== '' && !errors.edad && (
          <p className="text-xs fi-text-success flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" strokeWidth={1.5} aria-hidden="true" />
            Edad válida
          </p>
        )}
      </div>

      {/* Género */}
      <div className="fi-stack-sm">
        <label className="block text-sm font-semibold text-slate-200">
          Género <span className="fi-text-error">*</span>
        </label>
        <div className="grid grid-cols-3 gap-3">
          {[
            { value: 'masculino', label: 'Masculino' },
            { value: 'femenino', label: 'Femenino' },
            { value: 'otro', label: 'Otro' },
          ].map((option) => (
            <Button
              key={option.value}
              onClick={() => handleChange('genero', option.value)}
              className={`p-3 rounded-xl border-2 transition-all ${
                formData.genero === option.value
                  ? 'border-emerald-500 bg-emerald-950/30 shadow-lg'
                  : 'border-slate-700/50 bg-slate-900/40 hover:border-slate-600'
              }`}
              variant="ghost"
              size="sm"
              title={option.label}
            >
              <div className="mb-1"><UserRound className="w-6 h-6 mx-auto" strokeWidth={1.5} aria-hidden="true" /></div>
              <div className="fi-text-xs-medium text-slate-200">{option.label}</div>
            </Button>
          ))}
        </div>
        {touched.genero && errors.genero && (
          <p className="text-xs fi-text-error flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" strokeWidth={1.5} aria-hidden="true" />
            {errors.genero}
          </p>
        )}
      </div>

      {/* Motivo de Consulta (Optional) */}
      <div className="fi-stack-sm">
        <label htmlFor="motivoConsulta" className="block text-sm font-semibold text-slate-200">
          Motivo de consulta <span className="text-slate-500 text-xs">(opcional)</span>
        </label>
        <textarea
          id="motivoConsulta"
          value={formData.motivoConsulta}
          onChange={(e) => handleChange('motivoConsulta', e.target.value)}
          placeholder="Ej: Dolor de cabeza recurrente, mareos ocasionales"
          rows={3}
          className="w-full px-4 py-3 bg-slate-900/60 border-2 border-slate-700/50 rounded-xl text-slate-200 placeholder-slate-500 transition-all focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
        />
        <p className="fi-text-xs">
          {formData.motivoConsulta?.length || 0} / 500 caracteres
        </p>
      </div>

      {/* Form Validation Status */}
      <div className={`p-4 rounded-xl border-2 transition-all ${
        isFormValid()
          ? 'border-emerald-500/50 bg-emerald-950/20'
          : 'border-yellow-600/50 bg-yellow-950/20'
      }`}>
        <div className="fi-flex-gap-md">
          <span className="text-2xl">{isFormValid() ? <CheckCircle2 className="w-6 h-6 text-emerald-400" strokeWidth={1.5} aria-hidden="true" /> : <Timer className="w-6 h-6 text-yellow-400" strokeWidth={1.5} aria-hidden="true" />}</span>
          <div>
            <p className={`text-sm font-semibold ${isFormValid() ? 'text-emerald-300' : 'text-yellow-300'}`}>
              {isFormValid() ? 'Formulario completo' : 'Completa los campos requeridos'}
            </p>
            <p className="fi-text-xs mt-1">
              {isFormValid()
                ? 'Todos los datos son válidos. Revisa el preview HDF5 a la derecha.'
                : 'Nombre, edad y género son requeridos para continuar.'}
            </p>
          </div>
        </div>
      </div>

      {/* Skip with Demo Patient */}
      <div className="text-center pt-4 fi-border-top/50">
        <Button
          onClick={onSkipDemo}
          className="fi-subtitle hover:fi-text-success underline transition-colors duration-200"
          variant="ghost"
          size="sm"
          title="Saltar con paciente demo"
        >
          Saltar con paciente demo precargado →
        </Button>
      </div>
    </div>
  );
}
