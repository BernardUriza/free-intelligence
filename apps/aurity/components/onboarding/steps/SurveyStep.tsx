"use client";

/**
 * Survey Step - Personalization
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { StepProps, SurveyData, UserRole, ClinicType, AIExperience, ConsultasPerDay } from "../types";

const userRoleOptions = [
  { value: 'medico_general' as UserRole, label: 'Médico General', icon: '👨‍⚕️', desc: 'Atención primaria' },
  { value: 'especialista' as UserRole, label: 'Especialista', icon: '🩺', desc: 'Área especializada' },
  { value: 'enfermera' as UserRole, label: 'Enfermera/o', icon: '💉', desc: 'Cuidado directo' },
  { value: 'administrador' as UserRole, label: 'Administrador', icon: '📋', desc: 'Gestión clínica' },
];

const clinicTypeOptions = [
  { value: 'privada' as ClinicType, label: 'Privada', icon: '🏥' },
  { value: 'publica' as ClinicType, label: 'Pública', icon: '🏛️' },
  { value: 'mixta' as ClinicType, label: 'Mixta', icon: '🔄' },
];

const consultasOptions = [
  { value: '1-5' as ConsultasPerDay, label: '1-5', icon: '🔵' },
  { value: '6-15' as ConsultasPerDay, label: '6-15', icon: '🟢' },
  { value: '16-30' as ConsultasPerDay, label: '16-30', icon: '🟡' },
  { value: '31+' as ConsultasPerDay, label: '31+', icon: '🔴' },
];

const aiExperienceOptions = [
  { value: 'ninguna' as AIExperience, label: 'Ninguna', icon: '🌱', desc: 'Primera vez' },
  { value: 'basica' as AIExperience, label: 'Básica', icon: '🌿', desc: 'He probado algunas herramientas' },
  { value: 'avanzada' as AIExperience, label: 'Avanzada', icon: '🌳', desc: 'Uso frecuente' },
];

export function SurveyStep({ context, callbacks, status }: StepProps) {
  const [localSurvey, setLocalSurvey] = useState<SurveyData>(context.survey);

  const handleSelect = (field: keyof SurveyData, value: string) => {
    const newSurvey = { ...localSurvey, [field]: value };
    setLocalSurvey(newSurvey);
    callbacks.updateContext({ survey: newSurvey });
  };

  const isComplete = !!(
    localSurvey.userRole &&
    localSurvey.clinicType &&
    localSurvey.consultasPerDay &&
    localSurvey.aiExperience
  );

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      {/* Page Title */}
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-slate-50 mb-2">
          Personaliza tu experiencia
        </h2>
        <p className="text-slate-400">
          Ayúdanos a conocer tu práctica médica
        </p>
      </div>

      {/* Question 1: Rol */}
      <div className="space-y-4">
        <label className="fi-section-title-block">
          ¿Cuál es tu rol?
        </label>
        <div className="fi-grid-2">
          {userRoleOptions.map((option) => (
            <Button
              key={option.value}
              onClick={() => handleSelect('userRole', option.value)}
              className={`text-left ${localSurvey.userRole === option.value ? 'fi-survey-card-selected' : 'fi-survey-card'}`}
              variant="ghost"
              size="sm"
              title={option.label}
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">{option.icon}</span>
                <span className="font-semibold text-slate-200">{option.label}</span>
              </div>
              <p className="fi-text-xs">{option.desc}</p>
            </Button>
          ))}
        </div>
      </div>

      {/* Question 2: Tipo de clínica */}
      {localSurvey.userRole && (
        <div className="space-y-4 animate-fade-in-up">
          <label className="fi-section-title-block">
            ¿Tipo de clínica?
          </label>
          <div className="fi-grid-3">
            {clinicTypeOptions.map((option) => (
              <Button
                key={option.value}
                onClick={() => handleSelect('clinicType', option.value)}
                className={localSurvey.clinicType === option.value ? 'fi-survey-card-selected' : 'fi-survey-card'}
                variant="ghost"
                size="sm"
                title={option.label}
              >
                <div className="text-2xl mb-2">{option.icon}</div>
                <div className="font-semibold text-slate-200">{option.label}</div>
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Question 3: Consultas por día */}
      {localSurvey.clinicType && (
        <div className="space-y-4 animate-fade-in-up">
          <label className="fi-section-title-block">
            ¿Cuántas consultas atiendes al día?
          </label>
          <div className="fi-grid-4">
            {consultasOptions.map((option) => (
              <Button
                key={option.value}
                onClick={() => handleSelect('consultasPerDay', option.value)}
                className={localSurvey.consultasPerDay === option.value ? 'fi-survey-card-selected' : 'fi-survey-card'}
                variant="ghost"
                size="sm"
                title={option.label}
              >
                <div className="text-2xl mb-2">{option.icon}</div>
                <div className="font-semibold text-slate-200">{option.label}</div>
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Question 4: Experiencia con IA */}
      {localSurvey.consultasPerDay && (
        <div className="space-y-4 animate-fade-in-up">
          <label className="fi-section-title-block">
            ¿Experiencia previa con IA médica?
          </label>
          <div className="fi-grid-3">
            {aiExperienceOptions.map((option) => (
              <Button
                key={option.value}
                onClick={() => handleSelect('aiExperience', option.value)}
                className={localSurvey.aiExperience === option.value ? 'fi-survey-card-selected' : 'fi-survey-card'}
                variant="ghost"
                size="sm"
                title={option.label}
              >
                <div className="text-2xl mb-2">{option.icon}</div>
                <div className="font-semibold text-slate-200 mb-1">{option.label}</div>
                <p className="fi-text-xs">{option.desc}</p>
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Complete Button */}
      {isComplete && (
        <div className="text-center mt-12 animate-fade-in-up">
          <Button onClick={callbacks.next} disabled={status.busy} size="xl">
            Continuar con filosofía →
          </Button>
        </div>
      )}
    </div>
  );
}