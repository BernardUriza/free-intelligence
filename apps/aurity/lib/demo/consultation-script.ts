/**
 * Demo Consultation Script
 *
 * Realistic medical consultation dialogue for text-to-speech demo mode.
 * Uses Web Speech API to generate synthetic audio.
 *
 * Created: 2025-11-17
 */

export interface DialogueLine {
  speaker: 'doctor' | 'patient';
  text: string;
  pauseAfterMs?: number; // Optional pause after this line
}

/**
 * Realistic consultation script in Spanish (AURITY primary language)
 */
export const DEMO_CONSULTATION: DialogueLine[] = [
  {
    speaker: 'doctor',
    text: 'Buenos días, pase adelante por favor. ¿Cómo se encuentra el día de hoy?',
    pauseAfterMs: 2000,
  },
  {
    speaker: 'patient',
    text: 'Buenos días doctor. La verdad es que no me he sentido bien estos últimos días.',
    pauseAfterMs: 1500,
  },
  {
    speaker: 'doctor',
    text: '¿Cuándo comenzaron los síntomas? ¿Puede describirme qué es lo que siente?',
    pauseAfterMs: 2000,
  },
  {
    speaker: 'patient',
    text: 'Empezó hace como tres días. Tengo dolor de cabeza constante, y además me siento muy cansado. También he tenido un poco de fiebre.',
    pauseAfterMs: 2000,
  },
  {
    speaker: 'doctor',
    text: 'Entiendo. ¿Ha tomado la temperatura? ¿Qué tan alta ha sido la fiebre?',
    pauseAfterMs: 1500,
  },
  {
    speaker: 'patient',
    text: 'Sí, ayer me la tomé y tenía treinta y ocho punto cinco grados.',
    pauseAfterMs: 1500,
  },
  {
    speaker: 'doctor',
    text: 'De acuerdo. ¿Tiene alguna alergia a medicamentos que deba saber?',
    pauseAfterMs: 1500,
  },
  {
    speaker: 'patient',
    text: 'Sí doctor, soy alérgico a la penicilina.',
    pauseAfterMs: 1500,
  },
  {
    speaker: 'doctor',
    text: 'Muy bien, lo tomaré en cuenta. ¿Actualmente está tomando algún medicamento?',
    pauseAfterMs: 1500,
  },
  {
    speaker: 'patient',
    text: 'Sí, tomo lisinopril diez miligramos para la presión alta.',
    pauseAfterMs: 2000,
  },
  {
    speaker: 'doctor',
    text: 'Perfecto. Déjeme revisarlo. Voy a tomarle la presión arterial y escuchar sus pulmones.',
    pauseAfterMs: 3000,
  },
  {
    speaker: 'doctor',
    text: 'Su presión está en ciento cuarenta sobre noventa, un poco elevada. Los pulmones se escuchan bien, sin ruidos anormales.',
    pauseAfterMs: 2000,
  },
  {
    speaker: 'doctor',
    text: 'Basándome en los síntomas, parece ser una infección viral del tracto respiratorio superior. Voy a recetarle paracetamol para la fiebre y el dolor.',
    pauseAfterMs: 2000,
  },
  {
    speaker: 'doctor',
    text: 'Tome quinientos miligramos cada seis horas según sea necesario. Descanse mucho y tome abundantes líquidos.',
    pauseAfterMs: 2000,
  },
  {
    speaker: 'patient',
    text: '¿Necesito hacerme algún estudio?',
    pauseAfterMs: 1500,
  },
  {
    speaker: 'doctor',
    text: 'Por ahora no es necesario. Si los síntomas empeoran o la fiebre persiste más de cinco días, regrese para evaluación adicional.',
    pauseAfterMs: 2000,
  },
  {
    speaker: 'patient',
    text: 'Entendido doctor. Muchas gracias.',
    pauseAfterMs: 1000,
  },
  {
    speaker: 'doctor',
    text: 'Para servirle. Que se mejore pronto. Si tiene alguna duda, no dude en contactarme.',
    pauseAfterMs: 1000,
  },
];

/**
 * Expected medical entities that should be detected in transcription:
 * - Symptoms: dolor de cabeza, cansancio, fiebre
 * - Vital signs: 38.5°C, 140/90 mmHg
 * - Allergies: penicilina
 * - Current medications: lisinopril 10mg
 * - Diagnosis: infección viral del tracto respiratorio superior
 * - Treatment: paracetamol 500mg c/6h PRN
 */
