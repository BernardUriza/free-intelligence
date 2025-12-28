/**
 * useAISuggestions Hook
 *
 * Generates AI suggestions based on SOAP data.
 */

import { useState, useEffect } from 'react';
import type { SOAPData, AISuggestion } from '../types';

export function useAISuggestions(soapData: SOAPData): AISuggestion[] {
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);

  useEffect(() => {
    const timer = setTimeout(() => {
      const newSuggestions: AISuggestion[] = [];

      // Chest pain → EKG recommendation
      const chiefComplaint = soapData.chiefComplaint.toLowerCase();
      if (
        chiefComplaint.includes('dolor de pecho') ||
        chiefComplaint.includes('chest pain')
      ) {
        newSuggestions.push({
          type: 'suggestion',
          content: 'Considera EKG y Troponinas para descartar causas cardíacas',
          confidence: 0.9,
          source: 'Guías Clínicas',
        });
      }

      // High fever → blood culture
      const temperature = parseFloat(soapData.vitalSigns.temperature);
      if (!isNaN(temperature) && temperature > 38.5) {
        newSuggestions.push({
          type: 'suggestion',
          content:
            'Fiebre alta detectada. Considera biometría hemática y cultivos',
          confidence: 0.85,
          source: 'Protocolo Infeccioso',
        });
      }

      // Drug interaction warning
      const hasWarfarin = soapData.currentMedications.some((m) =>
        m.toLowerCase().includes('warfarin')
      );
      const hasAspirin = soapData.medications.some((m) =>
        m.name.toLowerCase().includes('aspirina')
      );
      if (hasWarfarin && hasAspirin) {
        newSuggestions.push({
          type: 'warning',
          content:
            'Interacción medicamentosa: Warfarin + Aspirina aumenta riesgo de sangrado',
          confidence: 0.95,
          source: 'Base de Datos de Interacciones',
        });
      }

      // General insight for respiratory symptoms
      if (soapData.chiefComplaint && soapData.vitalSigns.temperature) {
        newSuggestions.push({
          type: 'insight',
          content:
            'Paciente con síntomas respiratorios. Considerar etiología viral vs bacteriana según evolución',
          confidence: 0.75,
          source: 'Soporte de Decisión Clínica',
        });
      }

      setSuggestions(newSuggestions);
    }, 500);

    return () => clearTimeout(timer);
  }, [soapData]);

  return suggestions;
}
