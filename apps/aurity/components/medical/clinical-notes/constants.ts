/**
 * ClinicalNotes Constants
 */

import type { VitalSigns, Diagnosis, SOAPData } from './types';

export const POLLING_CONFIG = {
  maxAttempts: 30,
  intervalMs: 2000,
} as const;

export const DEFAULT_VITAL_SIGNS: VitalSigns = {
  temperature: '',
  heartRate: '',
  bloodPressure: '',
  respiratoryRate: '',
  oxygenSaturation: '',
};

export const NORMAL_VITAL_SIGNS: VitalSigns = {
  temperature: '36.5',
  heartRate: '72',
  bloodPressure: '120/80',
  respiratoryRate: '16',
  oxygenSaturation: '98',
};

export const INITIAL_SOAP_DATA: SOAPData = {
  chiefComplaint: '',
  hpi: '',
  allergies: [],
  currentMedications: [],
  vitalSigns: DEFAULT_VITAL_SIGNS,
  physicalExam: '',
  primaryDiagnosis: null,
  differentialDiagnoses: [],
  medications: [],
  diagnosticTests: [],
  followUp: '',
};

export const COMMON_ICD10: Diagnosis[] = [
  { code: 'J00', description: 'Resfriado común', severity: 'Leve' },
  { code: 'J06.9', description: 'Infección respiratoria aguda superior', severity: 'Leve' },
  { code: 'I10', description: 'Hipertensión esencial', severity: 'Moderada' },
  { code: 'E11.9', description: 'Diabetes tipo 2 sin complicaciones', severity: 'Moderada' },
  { code: 'R50.9', description: 'Fiebre no especificada', severity: 'Leve' },
  { code: 'R51', description: 'Cefalea', severity: 'Leve' },
  { code: 'J02.9', description: 'Faringitis aguda', severity: 'Leve' },
  { code: 'J20.9', description: 'Bronquitis aguda', severity: 'Moderada' },
];

export const COMMON_DIAGNOSTIC_TESTS = [
  'Biometría Hemática Completa',
  'Química Sanguínea',
  'Perfil de Lípidos',
  'Hemoglobina A1C',
  'Radiografía de Tórax',
  'Examen General de Orina',
  'Prueba COVID-19',
  'Electrocardiograma (EKG)',
] as const;
