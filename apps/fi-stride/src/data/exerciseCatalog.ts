/**
 * Exercise Catalog - Default exercises for FI-STRIDE
 * All exercises designed for accessibility (T21 athletes)
 */

import { Exercise } from '../services/exerciseStorage';

export const EXERCISE_CATALOG: Exercise[] = [
  {
    id: 'ex-001-walking',
    title: 'Caminata Suave',
    description: 'Camina a paso lento y regular. Perfecto para calentar.',
    duration: 120,
    difficulty: 'easy',
    videoUrl: 'https://example.com/walking.mp4',
    pictograms: ['🚶', '💨'],
    instructions: [
      'Ponte de pie, espalda recta',
      'Camina a paso normal',
      'Respira profundo',
      'Continúa 2 minutos',
    ],
    safetyAlerts: [
      'Si te mareas, detente y siéntate',
      'Mantén los ojos al frente',
    ],
    accessibility: {
      spacereduced: false,
      chair: false,
      noEquipment: true,
      lowImpact: true,
    },
    tags: ['cardio', 'warm-up', 'easy'],
  },
  {
    id: 'ex-002-stretching',
    title: 'Estiramientos Básicos',
    description: 'Estira los brazos y las piernas suavemente.',
    duration: 180,
    difficulty: 'easy',
    videoUrl: 'https://example.com/stretching.mp4',
    pictograms: ['🤸', '↗️'],
    instructions: [
      'Levanta los brazos lentamente',
      'Estira hacia el lado derecho',
      'Mantén 10 segundos',
      'Repite hacia el lado izquierdo',
      'Baja los brazos lentamente',
    ],
    safetyAlerts: ['No rebotes al estirar', 'Respira lentamente'],
    accessibility: {
      spacereduced: true,
      chair: true,
      noEquipment: true,
      lowImpact: true,
    },
    tags: ['flexibility', 'warm-up', 'easy'],
  },
  {
    id: 'ex-003-jumping-jacks',
    title: 'Saltos Simples',
    description: 'Salta suavemente abriendo y cerrando piernas.',
    duration: 60,
    difficulty: 'medium',
    videoUrl: 'https://example.com/jumping-jacks.mp4',
    pictograms: ['⬆️', '🦵'],
    instructions: [
      'Ponte de pie con los pies juntos',
      'Salta abriendo las piernas',
      'Salta cerrando las piernas',
      'Repite 20 veces',
    ],
    safetyAlerts: [
      'Salta suavemente, no muy alto',
      'Si tienes dolor en las rodillas, reduce la velocidad',
    ],
    accessibility: {
      spacereduced: false,
      chair: false,
      noEquipment: true,
      lowImpact: false,
    },
    tags: ['cardio', 'medium'],
  },
  {
    id: 'ex-004-squats',
    title: 'Sentadillas',
    description: 'Baja las caderas doblando las rodillas.',
    duration: 120,
    difficulty: 'medium',
    videoUrl: 'https://example.com/squats.mp4',
    pictograms: ['🦵', '⬇️'],
    instructions: [
      'Mantén los pies separados al ancho de los hombros',
      'Baja lentamente doblando las rodillas',
      'Mantén la posición 2 segundos',
      'Sube lentamente',
      'Repite 10 veces',
    ],
    safetyAlerts: [
      'Mantén la espalda recta',
      'No dejes que las rodillas pasen los pies',
    ],
    accessibility: {
      spacereduced: false,
      chair: false,
      noEquipment: true,
      lowImpact: true,
    },
    tags: ['strength', 'legs', 'medium'],
  },
  {
    id: 'ex-005-push-ups',
    title: 'Flexiones (Fácil)',
    description: 'Flexiones contra la pared o en la silla.',
    duration: 120,
    difficulty: 'medium',
    videoUrl: 'https://example.com/push-ups.mp4',
    pictograms: ['💪', '🧱'],
    instructions: [
      'Coloca las manos en la pared',
      'Inclínate hacia la pared doblando los codos',
      'Vuelve a la posición inicial',
      'Repite 10 veces',
    ],
    safetyAlerts: ['Mantén el cuerpo recto', 'Respira durante todo el ejercicio'],
    accessibility: {
      spacereduced: false,
      chair: true,
      noEquipment: false,
      lowImpact: true,
    },
    tags: ['strength', 'arms', 'medium'],
  },
  {
    id: 'ex-006-plank',
    title: 'Tabla (Plancha)',
    description: 'Mantén el cuerpo recto apoyado en manos y pies.',
    duration: 60,
    difficulty: 'hard',
    videoUrl: 'https://example.com/plank.mp4',
    pictograms: ['📏', '💪'],
    instructions: [
      'Apóyate en manos y pies',
      'Mantén el cuerpo en línea recta',
      'Aguanta 30 segundos',
      'Descansa',
      'Repite',
    ],
    safetyAlerts: [
      'No dejes caer las caderas',
      'Respira constantemente, no aguantes la respiración',
    ],
    accessibility: {
      spacereduced: false,
      chair: false,
      noEquipment: true,
      lowImpact: false,
    },
    tags: ['strength', 'core', 'hard'],
  },
  {
    id: 'ex-007-bicycles',
    title: 'Bicicleta Estática',
    description: 'Pedalea a ritmo moderado en una bicicleta.',
    duration: 300,
    difficulty: 'medium',
    videoUrl: 'https://example.com/bicycle.mp4',
    pictograms: ['🚴', '🔄'],
    instructions: [
      'Siéntate en la bicicleta',
      'Ajusta la altura del asiento',
      'Comienza a pedalear lentamente',
      'Aumenta gradualmente la velocidad',
      'Mantén un ritmo constante',
    ],
    safetyAlerts: [
      'Si sientes dolor en las rodillas, reduce la resistencia',
      'Mantente hidratado',
    ],
    accessibility: {
      spacereduced: true,
      chair: true,
      noEquipment: false,
      lowImpact: true,
    },
    tags: ['cardio', 'medium', 'equipment'],
  },
  {
    id: 'ex-008-yoga-basic',
    title: 'Yoga Básico',
    description: 'Poses simples de yoga para flexibilidad y relajación.',
    duration: 240,
    difficulty: 'easy',
    videoUrl: 'https://example.com/yoga.mp4',
    pictograms: ['🧘', '☮️'],
    instructions: [
      'Siéntate en el piso o en una silla',
      'Respira profundamente 5 veces',
      'Mueve lentamente hacia adelante',
      'Aguanta 30 segundos',
      'Vuelve a sentarte',
    ],
    safetyAlerts: [
      'No fuerces los estiramientos',
      'Detente si sientes dolor',
    ],
    accessibility: {
      spacereduced: true,
      chair: true,
      noEquipment: true,
      lowImpact: true,
    },
    tags: ['flexibility', 'relaxation', 'easy'],
  },
  {
    id: 'ex-009-dance',
    title: 'Baile Libre',
    description: 'Muévete al ritmo de la música que te gusta.',
    duration: 180,
    difficulty: 'medium',
    videoUrl: 'https://example.com/dance.mp4',
    pictograms: ['🎶', '💃'],
    instructions: [
      'Elige una canción que te guste',
      'Muévete libremente',
      'Sigue el ritmo',
      'Diviértete',
    ],
    safetyAlerts: ['Ten espacio suficiente alrededor', 'Usa ropa cómoda'],
    accessibility: {
      spacereduced: false,
      chair: false,
      noEquipment: true,
      lowImpact: false,
    },
    tags: ['cardio', 'fun', 'medium'],
  },
  {
    id: 'ex-010-cool-down',
    title: 'Enfriamiento',
    description: 'Baja el ritmo cardíaco con ejercicios suaves.',
    duration: 120,
    difficulty: 'easy',
    videoUrl: 'https://example.com/cool-down.mp4',
    pictograms: ['❄️', '😌'],
    instructions: [
      'Camina lentamente',
      'Estira los músculos',
      'Respira profundamente',
      'Relaja el cuerpo',
    ],
    safetyAlerts: [
      'No te sientes inmediatamente después de ejercitarte',
      'Toma agua lentamente',
    ],
    accessibility: {
      spacereduced: false,
      chair: true,
      noEquipment: true,
      lowImpact: true,
    },
    tags: ['cool-down', 'relaxation', 'easy'],
  },
];

export function getExercisesByDifficulty(
  difficulty: 'easy' | 'medium' | 'hard'
): Exercise[] {
  return EXERCISE_CATALOG.filter((ex) => ex.difficulty === difficulty);
}

export function getExercisesByTag(tag: string): Exercise[] {
  return EXERCISE_CATALOG.filter((ex) => ex.tags.includes(tag));
}

export function getAccessibleExercises(filter: keyof Exercise['accessibility']): Exercise[] {
  return EXERCISE_CATALOG.filter((ex) => ex.accessibility[filter]);
}
